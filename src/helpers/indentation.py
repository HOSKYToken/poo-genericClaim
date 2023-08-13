def indent_block(block, indent_level=0, indent_char=' '):
    indent = indent_char * indent_level
    out = ""
    for line in block.split('\n'):
        if len(line) > 0:
            if len(out) > 0:
                out += '\n'
            out += f"{indent}{line}"
    return out
