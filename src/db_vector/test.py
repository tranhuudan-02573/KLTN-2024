from typing import List

from langchain.docstore.document import Document as LangchainDocument
from langchain_community.document_loaders import PyMuPDFLoader, TextLoader, Docx2txtLoader

from src.config.app_config import get_settings
from src.db_vector.weaviate_rag_non_tenant import clean_input
from src.utils.app_util import count_token


def load_file(file_type: str, path: str) -> List[LangchainDocument]:
    try:
        loaders = {
            "pdf": PyMuPDFLoader,
            "txt": TextLoader,
            "docx": Docx2txtLoader
        }
        loader_class = loaders.get(file_type)
        if not loader_class:
            raise ValueError(f"Invalid file type: {file_type}")
        return loader_class(path).load()
    except Exception as e:
        print(f"An error occurred while loading the file: {str(e)}")
        return []


from sentence_transformers import SentenceTransformer

model = SentenceTransformer("../../final-model-v1")

settings = get_settings()

if __name__ == '__main__':
    text = ("Với cấu trúc trên, Axon Framework sẽ có thể tạo các instance của BorrowSaga mà không gặp phải Với cấu "
            "trúc trên, Axon Framework sẽ có thể tạo các instance của BorrowSaga mà không gặp phải Với cấu trúc trên, "
            "Axon Framework sẽ có thể tạo các instance của BorrowSaga mà không gặp phải Với cấu trúc trên, "
            "Axon Framework sẽ có thể tạo các instance của BorrowSaga mà không gặp phải Với cấu trúc trên, "
            "Axon Framework sẽ có thể tạo các instance của BorrowSaga mà không gặp phải Với cấu trúc trên, "
            "Axon Framework sẽ có thể tạo các instance của BorrowSaga mà không gặp phải Với cấu trúc trên, "
            "Axon Framework sẽ có thể tạo các instance của BorrowSaga mà không gặp phải Axon Axon Framework Framework "
            "Framework Framework Framework Framework Framework Framework Framework Framework Framework Framework "
            "Framework Fra Với cấu trúc trên, Axon Framework sẽ có thể tạo các instance của BorrowSaga mà không gặp phải Với cấu "
            "trúc trên, Axon Framework sẽ có thể tạo các instance của BorrowSaga mà không gặp phải Với cấu trúc trên, "
            "Axon Framework sẽ có thể tạo các instance của BorrowSaga mà không gặp phải Với cấu trúc trên, "
            "Axon Framework sẽ có thể tạo các instance của BorrowSaga mà không gặp phải Với cấu trúc trên, "
            "Axon Framework sẽ có thể tạo các instance của BorrowSaga mà không gặp phải Với cấu trúc trên, "
            "Axon Framework sẽ có thể tạo các instance của BorrowSaga mà không gặp phải Với cấu trúc trên, "
            "Axon Framework sẽ có thể tạo các instance của BorrowSaga mà không gặp phải Axon Axon Framework Framework "
            "Framework Framework Framework Framework Framework Framework Framework Framework mework Frameworkmewo Framework Framework "
            )
    # print(count_token(text))
    # print(model.encode(text))
    file_path = 'qchv_2021567.txt'  # Thay đổi đường dẫn đến file của bạn
    with open(file_path, 'r', encoding='utf-8') as file:
        content = file.read()
        print(len(content))
    # Làm sạch văn bản
    cleaned_content = clean_input(content)
    with open("tclean3.txt", 'w', encoding='utf-8') as file:
        file.write(cleaned_content)

    # In nội dung đã làm sạch ra màn hình (hoặc bạn có thể lưu vào file mới)
    print(cleaned_content)
    print(len(cleaned_content))
    # print(load_file("pdf", "./qchv_2021 (1).pdf"))
