class HuffmanEncoder(object):
    def __init__(self, huffman_code_list, huffman_code_list_lengths):
        self.huffman_code_list = huffman_code_list
        self.huffman_code_list_lengths = huffman_code_list_lengths

    def encode(self, bytes_to_encoded):
        final_num = 0
        final_int_len = 0
        for letter in bytes_to_encoded:
            bin_int_len = self.huffman_code_list_lengths[letter]
            bin_int = self.huffman_code_list[letter] & (2 ** (bin_int_len + 1) - 1)
            final_num <<= bin_int_len
            final_num |= bin_int
            final_int_len += bin_int_len
        bits_to_be_padded = (8 - (final_int_len % 8)) % 8
        final_num <<= bits_to_be_padded
        final_num |= (1 << (bits_to_be_padded)) - 1
        return bytes.fromhex(hex(final_num)[2:])
