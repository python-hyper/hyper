def _pad_binary(bin_str, req_len=8):
    return max(0, req_len - len(bin_str)) * '0' + bin_str

def _hex_to_bin_str(hex_string):
    unpadded_bin_string_list = map(bin, hex_string)
    padded_bin_string_list = map(_pad_binary, unpadded_bin_string_list)
    bitwise_message = "".join(padded_bin_string_list)
    return bitwise_message


class HuffmanDecoder(object):
    class _Node(object):
        def __init__(self, data):
            self.data = data
            self.mapping = {}

    def __init__(self, huffman_code_list, huffman_code_list_lengths):
        self.root = self._Node(None)
        for index, (huffman_code, code_length) in enumerate(zip(huffman_code_list, huffman_code_list_lengths)):
            self._insert(huffman_code, code_length, chr(index))

    def _insert(self, hex_number, hex_length, letter):
        hex_number = _pad_binary(bin(hex_number)[2:], hex_length)
        cur_node = self.root
        for digit in hex_number:
            if digit not in cur_node.mapping:
                cur_node.mapping[digit] = self._Node(None)
            cur_node = cur_node.mapping[digit]
        cur_node.data = letter

    def decode(self, encoded_string):
        number = _hex_to_bin_str(encoded_string)
        cur_node = self.root
        decoded_message = []
        for digit in number:
            if digit not in cur_node.mapping:
                break
            cur_node = cur_node.mapping[digit]
            if cur_node.data is not None:
                decoded_message.append(cur_node.data)
                cur_node = self.root
        return "".join(decoded_message)
