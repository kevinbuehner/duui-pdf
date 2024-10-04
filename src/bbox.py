from utils import remove_special_characters
import pandas as pd
import pdfplumber

def calculate_bbox(ocr_data: pd.DataFrame, block: int, page: int) -> str:
    """
    Calculate the bounding box for a specified block and page from OCR data.

    Args:
        ocr_data: A DataFrame containing Pytesseract OCR data or a path to a CSV file.
        block: The block number for which to calculate the bounding box.
        page: The page number for which to calculate the bounding box.
        
    Returns:
        (int): A bounding box (x0, top, x1, bottom)
        x0: The distance of left-most point from left side of page.
        x1: The distance of right-most point from left side of the page.
        top: The distance of highest point from top of page.
        bottom: The distance of lowest point from top of page.
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

    # Filter the DataFrame
    block_data = df[(df['block_num'] == block) & (df['page_num'] == page)]

    # Calculate the bounding box
    x0 = block_data['left'].min()
    x1 = (block_data['left'] + block_data['width']).max()
    top = block_data['top'].min()
    bottom = (block_data['top'] + block_data['height']).max()

    return (x0, top, x1, bottom)


def extract_text_from_bbox(pdf_file_path: str, bbox: (int), page: int) -> str:
    """
    Extract text for a specified bounding box from the PDF.

    Args:
        pdf_file_path: The path to the PDF.
        bbox: The bounding box values in pixels.
        page: The page number of the bounding box.
        
    Returns:
        str: The text that falls entirely within the bounding box.
    """ 

    # Used for scaling pixels (Pytesseract) to points (PDFPlumber)
    ocr_page_width = 1654
    ocr_page_height = 2339
    # Define a padding for the bounding box because Pytesseract's border includes text pixels
    # and PDFPlumber only extracts text that falls entirely within the bounding box
    padding = 3

    with pdfplumber.open(pdf_file_path) as pdf:
        pdf_page = pdf.pages[page-1]

        # Scale the pixels to points
        width_scale = pdf_page.width/ocr_page_width
        height_scale = pdf_page.height/ocr_page_height
        x0 = bbox[0] * width_scale - padding
        top = bbox[1] * height_scale - padding
        x1 = bbox[2] * width_scale + padding
        bottom = bbox[3] * height_scale + padding

        cropped_page = pdf_page.within_bbox((x0, top, x1, bottom))
        extracted_text = remove_special_characters(cropped_page.extract_text())

    return extracted_text


def convert_bbox_to_pixels(bbox: (int), pdf_file_path: str, page_number: int) -> tuple:
    """
    Converts a pdfplumber bounding box to OCR coordinates.

    Args:
        bbox: A tuple (x0, top, x1, bottom) from pdfplumber.
        pdf_file_path: A path to the PDF file to retrieve page dimensions.
        page_number: A page number (1-based) for the calculation.

    Returns: 
        Tuple (x0_ocr, top_ocr, x1_ocr, bottom_ocr): The OCR coordinates.
    """
    
    # Define the OCR page width and height (in pixels)
    ocr_page_width = 1654
    ocr_page_height = 2339

    # pdf_bbox: (x0, top, x1, bottom)
    x0_pdf, top_pdf, x1_pdf, bottom_pdf = bbox

    # Open the PDF file to get the width and height of the specified page
    with pdfplumber.open(pdf_file_path) as pdf:
        pdf_page = pdf.pages[page_number]
        pdf_page_width = pdf_page.width
        pdf_page_height = pdf_page.height

    # Calculate the scaling factors
    width_scale = ocr_page_width / pdf_page_width
    height_scale = ocr_page_height / pdf_page_height

    # Convert the pdfplumber BBox to OCR coordinates
    x0_ocr = x0_pdf * width_scale
    top_ocr = top_pdf * height_scale
    x1_ocr = x1_pdf * width_scale
    bottom_ocr = bottom_pdf * height_scale
    
    return (x0_ocr, top_ocr, x1_ocr, bottom_ocr)


def get_table_block_nums(ocr_data: pd.DataFrame, target_bbox: (int), page_num: int) -> list:
    """
    Get block numbers from OCR data where the text is within the target bounding box.
    Checks the next bounding box for the presence of a table caption.

    Args:
        ocr_data: The DataFrame containing OCR data with bounding box info and block numbers.
        target_bbox: The target bounding box (x0, top, x1, bottom).
        page_num: The page number to filter the OCR data.

    Returns: 
        set: A set of block numbers that are within the bounding box.
    """
    
    block_nums = set()
    x0_target, top_target, x1_target, bottom_target = target_bbox

    # Filter the DataFrame to get only the relevant page
    filtered_data = ocr_data[ocr_data['page_num'] == page_num + 1]
    
    # Iterate through the filtered OCR DataFrame
    for i in range(len(filtered_data)):
        row = filtered_data.iloc[i]
        
        # Unpack the OCR bounding box
        x0_ocr = row['left']
        top_ocr = row['top']
        x1_ocr = x0_ocr + row['width']
        bottom_ocr = top_ocr + row['height']
        
        # Check if the OCR bounding box overlaps with the target bounding box
        if (x0_ocr < x1_target and x1_ocr > x0_target and 
            top_ocr < bottom_target and bottom_ocr > top_target):
            # If overlap, add the block number to the list
            block_nums.add(row['block_num'])

            # Check the next bbox for "Table"
            if i + 1 < len(filtered_data):  # Ensure there is a next row
                next_row = filtered_data.iloc[i + 1]
                if "Table" in next_row['text']:  
                    block_nums.add(next_row['block_num'])
            
    return block_nums


def get_figure_block_nums(ocr_data: pd.DataFrame, target_bbox: (int), page_num: int) -> set:
    """
    Get block numbers from OCR data for figure caption that are located below the target bounding box.

    Args:
        ocr_data: DataFrame containing OCR data with bounding box info and block numbers.
        target_bbox: The target bounding box (x0, top, x1, bottom).
        page_num: The page number to filter the OCR data.

    Returns: 
        set: A set of block numbers that are below the bounding box.
    """

    block_nums = set()
    _, _, _, bottom_target = target_bbox

    # Filter the DataFrame to get only the relevant page
    filtered_data = ocr_data[ocr_data['page_num'] == page_num + 1]

    # Iterate through the filtered OCR DataFrame
    for i in range(len(filtered_data)):
        row = filtered_data.iloc[i]

        top_ocr = row['top']

        # Check if the OCR bounding box is below the target bounding box
        if top_ocr > bottom_target:
            if "Figure" in row['text']:
                block_nums.add(row['block_num'])
            break

    return block_nums

