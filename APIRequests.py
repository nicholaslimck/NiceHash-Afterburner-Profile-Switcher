import socket
import json


def dict_from_tcp(address, command):
    """
    Examples:
        dict_from_tcp(('127.0.0.1', '5100'),{ "id":1, "method":"algorithm.list", "params":[] }))
    Args:
        address: (tuple) IP address and port
        command: (dict) Commands

    Returns:
        dict: the response as a dict
    """
    excavator_address = address
    excavator_timeout = 10
    buf_size = 1024
    # command = { "id":1, "method":"algorithm.list", "params":[] }
    s = socket.create_connection(excavator_address, excavator_timeout)
    # send newline-terminated command
    s.sendall((json.dumps(command).replace('\n', '\\n') + '\n').encode())
    response = ''
    while True:
        chunk = s.recv(buf_size).decode()
        # excavator responses are newline-terminated too
        if '\n' in chunk:
            response += chunk[:chunk.index('\n')]
            break
        else:
            response += chunk
    s.close()

    response_data = json.loads(response)
    return response_data
