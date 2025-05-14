
from typing import Callable
import builtins
import streamlit as st

# Callback that the Streamlit app will register to capture output
_callback: Callable[[str], None] = None

def register_callback(cb: Callable[[str], None]):
    """
    Registra um callback para receber mensagens de saída.
    No Streamlit, chame `register_callback(lambda msg: st.session_state['chat_history'].append({'role':'assistant','content':msg}))`.
    """
    global _callback
    _callback = cb


def output(message: str):
    """
    Envia a mensagem para o Streamlit se o callback estiver registrado,
    caso contrário, cai no print padrão.
    """
    if _callback:
        _callback(message)
    else:
        builtins.print(message)


