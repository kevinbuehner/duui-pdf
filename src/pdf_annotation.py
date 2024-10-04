from utils import find_label, remove_special_characters
from bbox import calculate_bbox, extract_text_from_bbox
import base64
import re
from cassis import *
import pandas as pd
import pdfplumber

def get_text(pdf_path: str) -> str:
    """
    Extract the text from the PDF without special characters.

    Args:
        pdf_path: The path to the PDF.

    Returns:
        str: The extracted text of the PDF.
    """
    text = ""

    # Open the PDF with pdfplumber
    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            text += page.extract_text()

    # Remove special characters
    text = remove_special_characters(text)

    print(text[6975:7621])
    return text

def pdf_to_base64(path: str) -> str:
    """
    Encode PDF using base64.

    Args:
        path: The path to the PDF which will be encoded.

    Returns:
        str: Base64-encoded PDF.
    """
    with open(path, "rb") as pdf_file:
        encoded_string = base64.b64encode(pdf_file.read()).decode('utf-8')
    return encoded_string


def annotate_pdf(processed_data: pd.DataFrame, ocr_data: pd.DataFrame, pdf_file_path: str):
    """
    Annotate the Paper using the TypeSystem 'TexttechnologyPaperStructure.xml'.

    Args:
        processed_data: A DataFrame containing the segmentation.
        ocr_data: A DataFrame containing the OCR data.
        pdf_file_path: The path to the Paper which will be annotated.

    Returns:
        Cas: The CAS containing the encoded PDF as _InitialView, the text of the paper and
        the annotations regarding the TypeSystem.
    """
    typesystem = TypeSystem()
    with open('TexttechnologyPaperStructure.xml', 'rb') as f:
        typesystem = load_typesystem(f)

    # Create Cas
    cas = Cas(typesystem=typesystem)

    # Encode PDF as _InitialView
    cas.sofa_mime = r'application/pdf'
    cas.sofa_string = pdf_to_base64(pdf_file_path)

    # Define Type from the TypeSystem
    Headline = typesystem.get_type("org.texttechnologylab.annotation.paper.Headline")
    Title = typesystem.get_type("org.texttechnologylab.annotation.paper.Title")
    Author = typesystem.get_type("org.texttechnologylab.annotation.paper.Author")
    Abstract = typesystem.get_type("org.texttechnologylab.annotation.paper.Abstract")
    Keyword = typesystem.get_type("org.texttechnologylab.annotation.paper.Keyword")
    Section = typesystem.get_type("org.texttechnologylab.annotation.paper.Section")
    Table = typesystem.get_type("org.texttechnologylab.annotation.paper.Table")
    Figure = typesystem.get_type("org.texttechnologylab.annotation.paper.Figure")

    # Create a custom annotation view
    annotation_view = cas.create_view("annotation")
    
    # Extract the full PDF text
    pdf_text = get_text(pdf_file_path)

    # Set mime and sofa string
    annotation_view.sofa_mime = r'text/plain'
    annotation_view.sofa_string = pdf_text


    # Loop through each row in processed_data
    for index, row in processed_data.iterrows():
        block_num = row['block_num']
        page_num = row['page_num']
        
        # Calculate the bbox for the current block
        bbox = calculate_bbox(ocr_data, block_num, page_num)
        
        if row['Type'] == "Table":
            annotation = Table()
        elif row['Type'] == "Figure":
            annotation = Figure()
        else:
            # Extract the text from the bbox
            extracted_text = extract_text_from_bbox(pdf_file_path, bbox, page_num)
            
            # Find the start and end offsets of the extracted text in the full PDF text
            start_offset, end_offset = find_label(pdf_text, extracted_text)
            
            if start_offset is None or end_offset is None:
                continue  # Skip if the label is not found in the text

            # Create annotations for different types
            if row['Type'] == "Title":
                annotation = Title(begin=start_offset, end=end_offset)
            elif row['Type'] == "Author":
                annotation = Author(begin=start_offset, end=end_offset)
            elif row['Type'] == "Abstract":
                annotation = Abstract(begin=start_offset, end=end_offset)
            elif row['Type'] == "Keywords":
                annotation = Keyword(begin=start_offset, end=end_offset)
            elif row['Type'] == "Headline":
                annotation = Headline(begin=start_offset, end=end_offset)
            elif row['Type'] == "Section":
                level = row.get('level', None)
                label = row.get('label', None)
                index = row.get('index', None)

                annotation = Section(begin=start_offset, end=end_offset)
                
                if not pd.isna(level):
                    annotation.level = level
                if not pd.isna(label):
                    annotation.label = label
                if not pd.isna(index):
                    annotation.index = index

        # Add the annotation to the view
        annotation_view.add(annotation)

    # Save Cas to XMI
    cas.to_xmi("annotations.xmi")
    
    return cas
