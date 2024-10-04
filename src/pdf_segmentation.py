import pandas as pd
from bbox import calculate_bbox

def process_segmentation(segmentation_df: pd.DataFrame, ocr_data: pd.DataFrame) -> pd.DataFrame:
    """
    Process the segmentation DataFrame containing extracted segments from a PDF.
    Adds "Headline" entries for blocks that are above the title on any page.
    Also adds "Author" and "Section" entries that can be derived from the structure.
    
    Args:
        segmentation_df: DataFrame containing segmented data (Type, block_num, page_num).
        ocr_data: DataFrame containing OCR data with bounding box information (top, left, width, height).
        
    Returns:
        pd.DataFrame: The processed segmentation DataFrame with added "Headline" types.
    """
    
    new_headlines = []
    new_authors = []
    new_sections = []

    # Create a set of existing (block_num, page_num) tuples to avoid duplicates
    existing_entries = set(zip(segmentation_df['block_num'], segmentation_df['page_num']))

    # Iterate through the segmentation_df to find "Title"
    for _, row in segmentation_df.iterrows():
        if row['Type'] == "Title":
            title_block_num = row['block_num']
            title_page_num = row['page_num']
            
            # Get the bounding box for the title
            title_bbox = calculate_bbox(ocr_data, title_block_num, title_page_num)
            
            if title_bbox:
                _, title_top, _, _ = title_bbox
                
                # Check blocks above the title in the ocr_data
                for page_num in ocr_data['page_num'].unique():
                    above_title_blocks = ocr_data[(ocr_data['page_num'] == page_num) & 
                                                  (ocr_data['top'] < title_top)]
                    
                    for _, above_row in above_title_blocks.iterrows():
                        block_num = above_row['block_num']
                        # Ensure block_nums don't exist in segmentation_df
                        if (block_num, page_num) not in existing_entries:
                            # Collect new "Headline" entries
                            new_headlines.append({
                                "Type": "Headline",
                                "block_num": block_num,
                                "page_num": page_num
                            })
                            existing_entries.add((block_num, page_num))  # Add to the existing set

    # Convert new_headlines to a DataFrame and concatenate with segmentation_df
    if new_headlines:  # Check if there are new headlines to add
        headlines_df = pd.DataFrame(new_headlines)
        segmentation_df = pd.concat([segmentation_df, headlines_df], ignore_index=True)

    title_row = segmentation_df[segmentation_df['Type'] == 'Title']
    if not title_row.empty:
        title_block_num = title_row['block_num'].iloc[0]
        next_block_num = segmentation_df[
            (segmentation_df['page_num'] == 1) & 
            (segmentation_df['block_num'] != title_block_num)]['block_num'].min()
    else:
        title_block_num = None

    for _, row in ocr_data.drop_duplicates(subset=['block_num', 'page_num']).iterrows():
        block_num = row['block_num']
        page_num = row['page_num']

        # Check if this combination is not in segmentation_df
        if (block_num, page_num) not in existing_entries:
            if page_num == 1 and title_block_num < block_num < next_block_num:
                # Collect new "Author" entries
                new_authors.append({
                    "Type": "Author",
                    "block_num": block_num,
                    "page_num": page_num
                })
                existing_entries.add((block_num, page_num))
    
    # Identify all sections in the segmentation DataFrame
    sections = segmentation_df[segmentation_df['Type'] == 'Section']

    # Iterate over the sections to find ranges for new sections
    for i in range(len(sections) - 1):
        current_section = sections.iloc[i]
        next_section = sections.iloc[i + 1]
        
        # Get the current and next section block numbers
        current_block_num = current_section['block_num']
        next_block_num = next_section['block_num']
        
        # Check for each block_num in ocr_data if it lies between the two sections
        for _, row in ocr_data.drop_duplicates(subset=['block_num', 'page_num']).iterrows():
            block_num = row['block_num']
            page_num = row['page_num']

            # Check if the block_num is between current and next section block numbers
            if (block_num, page_num) not in existing_entries:
                if current_block_num < block_num < next_block_num:
                    new_sections.append({
                        "Type": "Section",
                        "block_num": block_num,
                        "page_num": page_num
                    })
                    existing_entries.add((block_num, page_num))

    # Convert new_authors and new_sections to DataFrames and concatenate with segmentation_df
    if new_authors:  # Check if there are new authors to add
        authors_df = pd.DataFrame(new_authors)
        segmentation_df = pd.concat([segmentation_df, authors_df], ignore_index=True)

    if new_sections:  # Check if there are new sections to add
        sections_df = pd.DataFrame(new_sections)
        segmentation_df = pd.concat([segmentation_df, sections_df], ignore_index=True)

    segmentation_df = segmentation_df.sort_values(by=['page_num', 'block_num']).reset_index(drop=True)

    return segmentation_df