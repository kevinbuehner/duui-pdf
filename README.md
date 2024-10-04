# duui-pdf

This project is a PDF processing application that utilizes Optical Character Recognition (OCR) to extract text and generate annotations based on specified structures in scientific papers. It uses various libraries to handle PDF files and OCR, and can be easily deployed using Docker.

## PyTesseract OCR

- ### [Tesseract-OCR](https://tesseract-ocr.github.io/tessdoc/)

|  **Parameter**   |  **Description**                                                                                             |
| ------------ | ------------------------------------------------------------------------------------------------------------ |
| `level`      | Indicates the hierarchy level of the recognized text: 1 = Page, 2 = Block, 3 = Paragraph, 4 = Line, 5 = Word |
| `page_num`   | The page number in the document                                                                              |
| `block_num`  | The block number within the page; a block is a contiguous area of text                                       |
| `par_num`    | The paragraph number within the block, where a block can contain multiple paragraphs                         |
| `line_num`   | The line number within the paragraph, where a paragraph can contain multiple lines of text                   |
| `word_num`   | The word number within the line, where a line can contain multiple words                                     |
| `left`       | The x-coordinate of the left edge, indicating how far the text is from the left side                         |
| `top`        | The y-coordinate of the top edge, indicating how far the text is from the top of the page                    |
| `width`      | The width of the recognized text (in pixels)                                                                 |
| `height`     | The height of the recognized text (in pixels)                                                                |
| `conf`       | The confidence value for the text recognition                                                                |
| `text`       | The recognized text or word (String)                                                                         |


## File Structure

- `main.py`: Main script that initiates the overall PDF processing and annotation tasks.
- `pdf_downloader.py`: Script for downloading PDF documents.
- `pdf_processor.py`: Functions for handling PyTesseract OCR and extractions.
- `pdf_segmentation.py`: Functions for segmenting PDF documents.
- `pdf_annotation.py`: Script for annotating PDF documents based on extracted OCR data.
- `bbox.py`: Functions to calculate bounding boxes for OCR text blocks.
- `utils.py`: Utility functions for text processing.
- `requirements.txt`: List of required Python packages.
- `config.json`: Configuration file for setting file paths.
- `TexttechnologyPaperStructure.xml`: XML file defining the TypeSystem used for annotating scientific papers.

## Docker

`docker build -t duui_pdf_reader .`
`docker run --rm -v ${PWD}:/app duui_pdf_reader`

## Python Libraries
- ### [Pytesseract](https://github.com/madmaze/pytesseract) `pip install pytesseract`
- ### [pandas](https://pandas.pydata.org/docs/index.html) `pip install pandas`
- ### [PyMuPDF](https://pymupdf.readthedocs.io/en/latest/) `pip install pymupdf`
- ### [pdfplumber](https://github.com/jsvine/pdfplumber) `pip install pdfplumber`
- ### [dkpro-cassis](https://github.com/dkpro/dkpro-cassis) `pip install dkpro-cassis`
- ### [Requests](https://requests.readthedocs.io/en/latest/) `pip install requests`
- ### [Levenshtein](https://github.com/rapidfuzz/python-Levenshtein) `pip install python-Levenshtein`