from utils import get_index
from bbox import convert_bbox_to_pixels, get_table_block_nums, get_figure_block_nums
from collections import defaultdict
import json
import pytesseract
import pandas as pd
from pdf2image import convert_from_path
import fitz
import pdfplumber
import Levenshtein

with open('config.json') as config_file:
    config = json.load(config_file)

tesseract_cmd = config['tesseract_cmd']
poppler_cmd = config['poppler_cmd']

pytesseract.pytesseract.tesseract_cmd = tesseract_cmd


def process_pdf(input_path: str, save_to_csv: bool) -> pd.DataFrame:
    """
    Execute Pytesseract for page segmentation and return output as DataFrame. 
    Optionally save the DataFrame as CSV.

    Args:
        input_path: The path of the PDF
        save_to_csv: Save the output of Pytesseract to a CSV file
        
    Returns:
        page_seg: Pytesseract output as DataFrame
    """

    # Convert PDF pages to images
    doc = convert_from_path(input_path, poppler_path=poppler_cmd)

    # DataFrame for Pytesseract Output
    page_list = []

    for id, page_data in enumerate(doc):
        page = pytesseract.image_to_data(page_data, lang='eng', config='csv --psm 3', output_type='data.frame')
        page.drop(page[page.text.isnull()].index, inplace=True)
        page = page[page['text'].str.strip() != '']
        # Set correct page_num because Pytesseract is executed for each page
        page['page_num'] = id + 1
        page_list.append(page)

    # Store all OCR data in DataFrame
    page_seg = pd.concat(page_list, ignore_index=True)

    # CSV output
    if save_to_csv:
        page_seg.to_csv(config['output_csv_path'], index=False)

    return page_seg


def find_block_num(chars: str, ocr_data: pd.DataFrame) -> tuple:
    """
    Find the block number and page number of the best matching OCR string 
    based on Levenshtein distance.

    Args:
        chars: The characters to compare.
        ocr_data: A DataFrame or CSV containing OCR data.

    Returns:
        tuple: The block number and page number corresponding to the best matching OCR string.

    Raises:
        ValueError: If the DataFrame is empty or does not contain the required columns.
    """

    # Check if ocr_data is a string (path to a CSV)
    if isinstance(ocr_data, str):
        # Load DataFrame from CSV
        df = pd.read_csv(ocr_data)
    elif isinstance(ocr_data, pd.DataFrame):
        # Use the provided DataFrame
        df = ocr_data
    else:
        raise ValueError("ocr_data must be either a DataFrame or a path to a CSV file.")

    # Check if DataFrame is empty or does not have the required columns
    if df.empty or not {'block_num', 'page_num', 'text'}.issubset(df.columns):
        raise ValueError("DataFrame must contain 'block_num', 'page_num', 'text' columns and cannot be empty.")

    # Normalized chars
    chars = chars.lower()
    # Group by block_num and page_num, and join texts
    grouped = df.groupby(['block_num', 'page_num'])['text'].apply(' '.join).reset_index()
    
    block_num = None
    page_num = None
    lowest_distance = float('inf')
    
    for _, row in grouped.iterrows():
        ocr_string = row['text'].lower()
        distance = Levenshtein.distance(chars, ocr_string)
        
        if distance < lowest_distance:
            lowest_distance = distance
            block_num = row['block_num']
            page_num = row['page_num']

    return block_num, page_num


def find_title(input_path: str) -> str:
    """
    Find the title by extracting the chars with the largest font on the first page.

    Args:
        input_path: The path to the PDF.

    Returns:
        str: A String containing the chars of the title.
    """
    pdf_plumber = pdfplumber.open(input_path)
    first_page = pdf_plumber.pages[0]

    # Get the characters from the first page
    chars = first_page.chars

    # Find the maximum font size (assuming the title has the largest size)
    max_font_size = max(char['size'] for char in chars)

    # Extract characters that match the largest font size
    title_chars = ''.join([char['text'] for char in chars if char['size'] == max_font_size])
    
    return title_chars


# TODO implement an alternative method for extracting section headings
def find_sections(input_path: str):
    """
    Find the section headings by extracting the outline.
    Note: This method relies on the outline being defined.

    Args:
        input_path: The path to the PDF.

    Returns:
        [str]: A list of strings where each string contains the chars of the section heading.
    """
    pdf_fitz = fitz.open(input_path)
    outline = pdf_fitz.get_toc(simple=True)

    return get_index(outline)


def find_tables(pdf_path: str, ocr_data: pd.DataFrame):
    """
    Find the tables by using PyMuPDF .find_tables().
    Note: This function relies on a table extraction algorithm.

    Args:
        pdf_path: The path to the PDF.
        ocr_data: A DataFrame containing OCR data.

    Returns:
        defaultdict(list): A dict where key represents a page number 
        and value a list of block numbers.
    """
    tables_block_nums = defaultdict(list)

    with pdfplumber.open(pdf_path) as pdf:
        # Extract tables for every page
        for page_num in range(len(pdf.pages)):
            page = pdf.pages[page_num]
            tables = page.find_tables()

            # If tables are found
            for table in tables:
                # Convert bbox to OCR pixels
                ocr_bbox = convert_bbox_to_pixels(table.bbox, pdf_path, page_num)
                # Find the block_num of the table with the corresponding page_num
                tables_block_nums[page_num+1] += (get_table_block_nums(ocr_data, ocr_bbox, page_num))

    return tables_block_nums


def find_figures(pdf_file_path: str, ocr_data: pd.DataFrame):
    """
    Find the figures by using PyMuPDF .images.

    Args:
        pdf_file_path: The path to the PDF.
        ocr_data: A DataFrame containing OCR data.

    Returns:
        defaultdict(list): A dict where key represents a page number 
        and value a list of block numbers.
    """
    figures_block_nums = defaultdict(list)

    with pdfplumber.open(pdf_file_path) as pdf:
        for page_number in range(len(pdf.pages)):
            pdf_page = pdf.pages[page_number]

            # Extract images from the current page
            images = pdf_page.images

            for image in images:
                # Each image is a dictionary
                x0 = image['x0']
                top = image['top']
                x1 = image['x1']
                bottom = image['bottom']
                image_bbox = convert_bbox_to_pixels((x0, top, x1, bottom), pdf_file_path, page_number)
                figures_block_nums[page_number+1] += (get_figure_block_nums(ocr_data, image_bbox, page_number))

    return figures_block_nums


def find_abstract(ocr_data: pd.DataFrame) -> set:
    """
    Find the block number for the section containing "abstract" on the first page.
    If the block only contains the word "abstract," include the next block number.

    Args:
        ocr_data: DataFrame containing OCR data with bounding box info and block numbers.

    Returns:
        set: A set containing the block number and, if applicable, the next block number.
    """
    search_string = "abstract"
    block_nums = set()

    # Filter the OCR data for the first page
    first_page_data = ocr_data[ocr_data['page_num'] == 1]

    # Iterate through the rows of the first page's OCR data
    for index, row in first_page_data.iterrows():
        # Normalize the text to lowercase
        normalized_text = row['text'].strip().lower()

        # Check if the text contains the word "abstract"
        if search_string in normalized_text:
            # Add the block number
            block_nums.add(row['block_num'])

            # If the block only contains the word "abstract," add the next block number
            if normalized_text == search_string:
                next_index = index + 1
                if next_index < len(first_page_data):
                    next_block_num = first_page_data.iloc[next_index]['block_num']
                    block_nums.add(next_block_num)
            break  # Exit after the first occurrence

    return block_nums


def find_keywords(ocr_data: pd.DataFrame) -> set:
    """
    Find the block number for the section containing "keywords" on the first page.
    If the block only contains the word "keywords," include the next block number.

    Args:
        ocr_data: DataFrame containing OCR data with bounding box info and block numbers.

    Returns:
        set: A set containing the block number and, if applicable, the next block number.
    """
    search_string = "keywords"
    block_nums = set()

    # Filter the OCR data for the first page
    first_page_data = ocr_data[ocr_data['page_num'] == 1]

    # Iterate through the rows of the first page's OCR data
    for index, row in first_page_data.iterrows():
        # Normalize the text to lowercase
        normalized_text = row['text'].strip().lower()

        # Check if the text contains the word "keywords"
        if search_string in normalized_text:
            # Add the block number
            block_nums.add(row['block_num'])

            # If the block only contains the word "keywords," add the next block number
            if normalized_text == search_string:
                next_index = index + 1
                if next_index < len(first_page_data):
                    next_block_num = first_page_data.iloc[next_index]['block_num']
                    block_nums.add(next_block_num)
            break  # Exit after the first occurrence

    return block_nums

