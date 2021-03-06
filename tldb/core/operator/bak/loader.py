from pathlib import Path
from config import root_path
from tldb.core.index_structure.rtree import RTree
from tldb.core.structure.entry import Entry
from tldb.core.structure.dewey_id import DeweyID
from tldb.core.structure.node import XMLNode

import numpy as np
import logging
import timeit


data_path = root_path() / 'tests' / 'io' / 'in' / 'cases'


def get_index_highest_element(all_elements_name: [str], table_name: str) -> int:
    """Summary
    This function return the index of highest level element (in XML query) of a table name
    e.g: If query is A->B then all_elements_name would be ['A', 'B']
    get_index_highest_element(['A, B'], 'B_A') returns 1

    :param all_elements_name: list of elements in XML query by level order
    :param table_name:
    :return: index of highest element
    """
    table_elements = table_name.split('_')
    index = []
    for element_name in table_elements:
        index.append(all_elements_name.index(element_name))
    return np.argmin(np.asarray(index))


def load_text_file(file_path: Path) -> [str]:
    """Summary
    Load text file by lines

    :param file_path: path to file
    :return: lines
    """

    with file_path.open() as f:
        content = f.readlines()
    content = [x.strip() for x in content]
    return content


def load_xml_entries(folder_name: str, element_name: str) -> [Entry]:
    """Summary
    load XML Entry from a file in the following format:
    Entry[0] = id, Entry[1] = value

    :param folder_name:
    :param element_name
    :return: list of loaded entries
    """
    id_file_path = data_path / folder_name / (element_name + '_id.dat')
    value_file_path = data_path / folder_name / (element_name + '_v.dat')
    ids = load_text_file(id_file_path)
    values = load_text_file(value_file_path)
    if len(ids) != len(values):
        raise ValueError('Id and value files have different size')
    entries = []
    for i in range(len(ids)):
        entries.append(Entry([DeweyID(ids[i]), float(values[i])]))  # Convert value from string to int
    return entries


def load_sql_entries(file_path: Path) -> [Entry]:
    """Summary
    This function load contents of the SQL table file and put them as coordinate in Entry

    :param file_path
    :return: loaded entries
    """
    content = load_text_file(file_path)
    entries = []
    for i in range(len(content)):
        entries.append(Entry([float(x) for x in content[i].split()]))  # Convert list of string -> list of int
    return entries


def load_elements(folder_name: str, all_elements_name: [str], max_n_children: int, load_method: str):
    """Summary
    Load elements and return list of root node of each element's R_Tree

    :param folder_name:
    :param all_elements_name:list of name of elements in XML query
    :param max_n_children: maximum number of children in a node
    :param load_method: name of bulk loading method
    :return: dict with key is name of element and value is corresponding root node of RTree_XML
    """
    logger = logging.getLogger("Loader")
    all_elements_root = {}
    for element_name in all_elements_name:
        logger.debug('Loading element: ' + element_name)

        start_loading = timeit.default_timer()

        element_entries = load_xml_entries(folder_name, element_name)
        rtree_xml = RTree()
        rtree_xml.load(element_entries, load_method, 1, XMLNode, max_n_children)
        # rtree_xml.load(element_entries, element_name, max_n_children)
        all_elements_root[element_name] = rtree_xml.root

        end_loading = timeit.default_timer()
        logger.debug('%s %d', 'Loading element took:', end_loading - start_loading)
    return all_elements_root


def load_tables(folder_name, all_elements_name, max_n_children, load_method):
    """Summary
    Load all tables inside a folder (files that end with _table.dat)

    :param folder_name:
    :param all_elements_name:
    :param max_n_children:
    :param load_method
    :return: dict with key is name of table and value is corresponding root node of SQLRTree
    """
    """
    Args:
        folder_name (string):
        all_elements_name (list of string): list of elements in XML query
        max_n_children (int): maximum number of children in R_Tree

    Returns:
        all_tables_root (dict[string, Node]): 
    """
    logger = logging.getLogger("Loader")
    all_tables_root = {}
    path = data_path / folder_name
    for file_path in path.glob('*_table.dat'):
        table_name = file_path.name[:-10]
        logger.debug('%s %s', 'Loading table:', table_name)
        start_loading = timeit.default_timer()
        table_entries = load_sql_entries(file_path)
        # dimension = get_index_highest_element(all_elements_name, table_name)
        rtree_sql = RTree()
        rtree_sql.load(entries=table_entries, method=load_method, dimension=1, max_n_children=max_n_children)
        all_tables_root[table_name] = rtree_sql.root

        end_loading = timeit.default_timer()
        logger.debug('%s %d', 'Loading table:', end_loading - start_loading)
    return all_tables_root


def load_xml_query(folder_name: str) -> ([str], [[int]]):
    """Summary
    Load XML query from a folder in a XML_query.data file
    The file must be in the following format:
    - First line: Elements name in query of level order format
    - Following lines: Containing the relationship matrix telling the relationship between each element
        + 1 = parent children
        + 2 = ancestor descendant

    :param folder_name: name of the folder containing XML query file
    :return: element names and relationship matrix
    """

    xml_query_file_path = data_path / folder_name / "XML_query.dat"
    with xml_query_file_path.open() as f:
        content = f.readlines()
    content = [x.strip() for x in content]

    all_elements_name = content[0].split(" ")

    relationship_matrix = np.zeros((len(all_elements_name), len(all_elements_name)))

    for i in range(1, len(content)):
        relationship = content[i].split(" ")
        relationship_matrix[all_elements_name.index(relationship[0]), all_elements_name.index(relationship[1])] \
            = int(relationship[2])

    return all_elements_name, relationship_matrix


class Loader:
    """Summary
    This loader takes a folder path read the XML query by looking for a "XML_query.data" file
    It will then load all elements root given that each element will have a element_v.dat for elemnt value and element_id.dat for element Dewey index
    It will load all tables (files that contains "tables" in its name)
    Attributes:
        max_n_children (int): maximum number of children in a RTree Node
        all_elements_name ([str]): list of element names of the XML query in level order
        all_elements_root ([Node]): list of root nodes of each element in the XML query
        all_tables_root ([Node]): list of root nodes of each table

    """

    def __init__(self, folder_name: str, max_n_children: int, load_method: str):
        logger = logging.getLogger("Loader")
        logger.info("Loader started")
        start_loading = timeit.default_timer()
        self.method = load_method
        self.max_n_children = max_n_children
        self.all_elements_name, self.relationship_matrix = load_xml_query(folder_name)
        self.all_elements_root = load_elements(folder_name, self.all_elements_name, self.max_n_children, load_method)
        self.all_tables_root = load_tables(folder_name, self.all_elements_name, self.max_n_children, load_method)
        end_loading = timeit.default_timer()
        self.total_loading_time = end_loading - start_loading
        logger.info('%s %.3f', "Total loading time:", self.total_loading_time)
