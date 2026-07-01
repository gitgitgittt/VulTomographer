import tree_sitter_c as tsc
from tree_sitter import Language, Parser


class ASTSymbolAnalyzer:
    def __init__(self):
        self.C_LANGUAGE = Language(tsc.language())
        self.parser = Parser(self.C_LANGUAGE)

    def _traverse_ast(self, node, code_bytes, identifiers, declarations):

        if node.type in ['identifier', 'type_identifier', 'field_identifier']:
            ident_name = code_bytes[node.start_byte:node.end_byte].decode('utf8')
            identifiers.add(ident_name)

            parent = node.parent
            if parent and parent.type in ['function_declarator', 'init_declarator', 'struct_specifier']:
                declarations.add(ident_name)

        for child in node.children:
            self._traverse_ast(child, code_bytes, identifiers, declarations)

    def extract_undefined_symbols(self, code_snippet: str) -> list:

        code_bytes = code_snippet.encode('utf8')
        tree = self.parser.parse(code_bytes)

        all_identifiers = set()
        local_declarations = set()

        self._traverse_ast(tree.root_node, code_bytes, all_identifiers, local_declarations)

        c_keywords = {
            'int', 'char', 'void', 'long', 'short', 'unsigned', 'signed', 'float', 'double',
            'struct', 'union', 'enum', 'typedef', 'sizeof', 'if', 'else', 'return', 'for',
            'while', 'do', 'switch', 'case', 'break', 'continue', 'default', 'goto', 'NULL'
        }

        undefined_symbols = (all_identifiers - local_declarations) - c_keywords

        return list(undefined_symbols)


if __name__ == "__main__":
    analyzer = ASTSymbolAnalyzer()
    mock_code = """

    """
    symbols = analyzer.extract_undefined_symbols(mock_code)
