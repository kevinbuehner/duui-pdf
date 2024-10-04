import re

def get_index(sections: list) -> list:
    """
    Find the index of a section (1, 1.1, 1.1.1, ...).

    Args:
        [[int, str, int]]: The outline extracted from PyMuPDFs .get_toc(simple=True) method.
        The data structure is [[level, 'section', page]].

    Returns:
        [[int, str, int, str]]: The index (1, 1.1, 1.1.1, ...) is added to the list. 
        The new data structure is [[level, 'section', page, 'index']].
    """
    for id, e in enumerate(sections):
        if id == 0:
            e.append('1')
        else:
            level_pre, _, _, index_pre = sections[id-1]
            if e[0] == 1:
                e.append(str(int(index_pre[0]) + 1))
            elif level_pre < e[0]:
                e.append(index_pre + '.1')
            else:
                e.append(index_pre[:-2] + '.' + str(int(index_pre[-1])+ 1))
    return sections


def find_label(text: str, label: str) -> str:
    """
    Find the start and end position of a given label in the text string.

    Args:
        text: The string to be searched.
        label: The string to find in text.

    Returns:
        str: start and end position if the label was found in the text.
    """
    label = remove_special_characters(label)
    
    start = text.find(label)
    end = start + len(label)

    return start, end


def remove_special_characters(text: str) -> str:
    """
    Removes special characters from a given string.

    Args:
        text: The string to clean.

    Returns:
        str: The clean input string.
    """
    text = re.sub(r'[\x00-\x09\x0B-\x1F]', '', text)
    return text