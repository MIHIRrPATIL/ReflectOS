import sys
import types

def apply_patches():
    """
    Applies monkeypatches for Eventlet (if present), PaddleOCR and LangChain compatibility.
    """
    # --- MONKEYPATCH EVENTLET FOR NON-BLOCKING I/O ---
    try:
        import os
        # CRITICAL: Must be set BEFORE importing eventlet, because greendns is loaded at import time.
        # Eventlet's greendns resolver is notoriously broken on Windows and prevents
        # httplib2/google-api-python-client from resolving any domain names.
        os.environ["EVENTLET_NO_GREENDNS"] = "yes"
        import eventlet
        eventlet.monkey_patch()
        print("[SYSTEM] Eventlet monkeypatch applied (greendns disabled).")
    except ImportError:
        pass

    # --- SHIM FOR LANGCHAIN DOCS ---
    try:
        import langchain.docstore.document
    except ImportError:
        if "langchain.docstore" not in sys.modules:
            sys.modules["langchain.docstore"] = types.ModuleType("langchain.docstore")
        
        if "langchain.docstore.document" not in sys.modules:
            doc_module = types.ModuleType("langchain.docstore.document")
            try:
                from langchain_core.documents import Document
            except ImportError:
                try:
                    from langchain.schema import Document
                except ImportError:
                    class Document: pass
            doc_module.Document = Document
            sys.modules["langchain.docstore.document"] = doc_module
            sys.modules["langchain.docstore"].document = doc_module

    # --- SHIM FOR LANGCHAIN TEXT SPLITTERS ---
    try:
        import langchain.text_splitter
    except ImportError:
        if "langchain.text_splitter" not in sys.modules:
            ts_module = types.ModuleType("langchain.text_splitter")
            try:
                from langchain_text_splitters import RecursiveCharacterTextSplitter
            except ImportError:
                try:
                    from langchain.text_splitter import RecursiveCharacterTextSplitter
                except ImportError:
                    class RecursiveCharacterTextSplitter: pass
            
            ts_module.RecursiveCharacterTextSplitter = RecursiveCharacterTextSplitter
            sys.modules["langchain.text_splitter"] = ts_module
