from nbconvert.preprocessors import Preprocessor
import re


# as per https://stackoverflow.com/questions/42255564/how-to-export-and-preserve-linked-jupyter-notebooks
class NotebookLinksProcessor(Preprocessor):

    def preprocess_cell(self, cell, resources, index):

        if 'source' in cell and cell.cell_type == "markdown":
            cell.source = re.sub(r"\[([^]]*)\]\(([^)]*)\.ipynb\)",r"[\1](\2.html)",cell.source)

        return cell, resources