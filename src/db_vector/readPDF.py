from fpdf import FPDF


def create_pdf_from_text(text, output_pdf_path):
    # Khởi tạo PDF
    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)

    # Thêm trang và thiết lập font Unicode (DejaVuSans)
    pdf.add_page()
    pdf.add_font('DejaVuSansCondensed', '', r'C:\Users\danla\Downloads\DejaVu_Sans\DejaVuSansCondensed.ttf', uni=True)
    pdf.set_font("DejaVuSansCondensed", size=5)  # Kích thước font có thể được điều chỉnh theo nhu cầu

    # Thêm nội dung văn bản vào PDF
    pdf.multi_cell(0, 10, text)

    # Lưu file PDF
    pdf.output(output_pdf_path)


# Đọc nội dung file text 
def read_text_file(file_path):
    with open(file_path, "r", encoding="utf-8") as file:
        return file.read()


# Tạo file PDF từ văn bản
create_pdf_from_text(read_text_file("./t"), "output3.pdf")
