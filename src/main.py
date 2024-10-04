import json
from pdf_downloader import download_file
from pdf_processor import *
from pdf_annotation import annotate_pdf
from pdf_segmentation import process_segmentation

with open('config.json') as config_file:
    config = json.load(config_file)


def main():
    # Download PDF and store the path
    # pdf_url = config['pdf_url']
    # pdf_path = download_file(pdf_url)
    
    pdf_path = r'pdf-src/tests/lrec2022-example.pdf'

    # Load Pytesseract OCR output into DataFrame
    ocr_dataframe = process_pdf(pdf_path, save_to_csv=True)
    # Optionally save OCR output as CSV
    ocr_csv = config['output_csv_path']

    # Extraction
    segments = []

    title_chars = find_title(pdf_path)
    title_block_num, title_page_num = find_block_num(title_chars, ocr_dataframe)
    segments.append({"Type": "Title", "block_num": title_block_num, "page_num": title_page_num})

    abstract_block_nums = find_abstract(ocr_dataframe)
    for abstract_block_num in abstract_block_nums:
        segments.append({"Type": "Abstract", "block_num": abstract_block_num, "page_num": 1})

    keywords_block_nums = find_keywords(ocr_dataframe)
    for keywords_block_num in keywords_block_nums:
        segments.append({"Type": "Keywords", "block_num": keywords_block_num, "page_num": 1})

    outline = find_sections(pdf_path)
    for item in outline:
        # Filter the OCR DataFrame by the specific page number
        filtered_ocr_data = ocr_dataframe[ocr_dataframe['page_num'] == item[2]]
        section_block_num, _ = find_block_num(item[1].strip(" "), filtered_ocr_data)
        segments.append({"Type": "Section", 
                         "block_num": section_block_num, 
                         "page_num": item[2],
                         "level": int(item[0]-1),
                         "label": item[1],
                         "index": item[3]})
    
    tables = find_tables(pdf_path, ocr_dataframe)
    if tables:
        for page_num in tables:
            for table in tables[page_num]:
                table_block_num, table_page_num = table, page_num
                segments.append({"Type": "Table", "block_num": table_block_num, "page_num": table_page_num})

    figures = find_figures(pdf_path, ocr_dataframe)
    if figures:
        for page_num in figures:
            for figure in figures[page_num]:
                figure_block_num, figure_page_num = figure, page_num
                segments.append({"Type": "Figure", "block_num": figure_block_num, "page_num": figure_page_num})

    segmentation_dataframe = process_segmentation(pd.DataFrame(segments), ocr_dataframe)
    # Segmentation DataFrame to CSV
    segmentation_dataframe.to_csv('segmentation.csv', index=False)

    # Annotation
    annotate_pdf(processed_data=segmentation_dataframe, ocr_data=ocr_dataframe, pdf_file_path=pdf_path)


if __name__ == "__main__":
    main()
