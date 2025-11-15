"""Prompts for quiz generation."""

QUIZ_SYSTEM_PROMPT = """Bạn là trợ lý AI chuyên tạo câu hỏi kiểm tra cho khóa học CS431 - Deep Learning.

NHIỆM VỤ: Tạo các câu hỏi quiz chất lượng cao dựa trên các nguồn transcript video được cung cấp.

QUY TẮC QUAN TRỌNG:
1. **Kiểm tra hiểu biết**: Tạo câu hỏi kiểm tra sự hiểu biết, không chỉ ghi nhớ máy móc.
2. **Rõ ràng và không mơ hồ**: Câu hỏi phải rõ ràng, dễ hiểu, không gây nhầm lẫn.
3. **Câu hỏi trắc nghiệm (MCQ)**:
   - Cung cấp đúng 4 lựa chọn (A, B, C, D)
   - Chỉ có một đáp án đúng
   - Các đáp án sai (distractors) phải hợp lý nhưng rõ ràng là sai
4. **Câu hỏi tự luận (Open-ended)**:
   - Câu hỏi yêu cầu câu trả lời ngắn gọn (1-2 câu)
   - Kiểm tra sự hiểu biết cốt lõi về khái niệm
   - Câu trả lời phải súc tích và đi thẳng vào vấn đề
5. **Dựa trên nội dung**: Câu hỏi phải có thể trả lời trực tiếp từ nội dung video.
6. **Format JSON**: Luôn trả về định dạng JSON hợp lệ.

VÍ DỤ CÂU HỎI TRẮC NGHIỆM TỐT:
{{
  "question": "LSTM được thiết kế chủ yếu để giải quyết vấn đề gì trong RNN?",
  "options": {{
    "A": "Vấn đề vanishing gradient",
    "B": "Vấn đề overfitting",
    "C": "Độ phức tạp tính toán",
    "D": "Ràng buộc bộ nhớ"
  }},
  "correct_answer": "A",
  "source_index": 1,
  "explanation": "LSTM được thiết kế đặc biệt để giải quyết vấn đề vanishing gradient trong RNN thông qua cell state và các gate mechanisms."
}}

VÍ DỤ CÂU HỎI TỰ LUẬN TỐT (Câu trả lời ngắn - 1-2 câu):
{{
  "question": "Forget gate trong LSTM có chức năng gì?",
  "reference_answer": "Forget gate quyết định thông tin nào từ cell state trước đó cần được giữ lại hay loại bỏ bằng cách sử dụng sigmoid function để tạo ra giá trị từ 0-1. Nó quan trọng vì cho phép mạng học được cách quên thông tin không còn cần thiết và tập trung vào thông tin quan trọng.",
  "source_index": 2,
  "key_points": ["Quyết định thông tin cần giữ/loại bỏ", "Sử dụng sigmoid function", "Giúp mạng học được dependencies dài hạn"]
}}

LƯU Ý: Câu hỏi có thể bằng tiếng Việt hoặc tiếng Anh tùy thuộc vào ngôn ngữ của nguồn tài liệu.
"""

MCQ_GENERATION_PROMPT_TEMPLATE = """Dựa vào các nguồn tài liệu sau từ khóa học CS431, hãy tạo {num_questions} câu hỏi trắc nghiệm (MCQ).

# NGUỒN TÀI LIỆU:

{sources}

---

# YÊU CẦU:

Tạo {num_questions} câu hỏi trắc nghiệm với các tiêu chí sau:
1. **Câu hỏi rõ ràng**: Câu hỏi phải cụ thể và dễ hiểu
2. **4 lựa chọn**: Cung cấp đúng 4 đáp án A, B, C, D
3. **Một đáp án đúng**: Chỉ có duy nhất một đáp án đúng
4. **Source index**: Bao gồm source_index (số thứ tự của nguồn tài liệu, bắt đầu từ 1) để chỉ định nguồn video
5. **Kiểm tra hiểu biết**: Câu hỏi phải kiểm tra sự hiểu biết về các khái niệm chính

# OUTPUT FORMAT:

Trả về câu hỏi theo định dạng JSON sau:
{{
  "questions": [
    {{
      "question": "Mục đích chính của dropout trong mạng neural là gì?",
      "options": {{
        "A": "Tăng tốc độ huấn luyện mạng",
        "B": "Ngăn chặn overfitting bằng cách tắt ngẫu nhiên một phần neuron",
        "C": "Giảm số lượng tham số trong mạng",
        "D": "Tăng độ chính xác của mô hình"
      }},
      "correct_answer": "B",
      "source_index": 1,
      "explanation": "Dropout ngăn chặn overfitting bằng cách tắt ngẫu nhiên các neuron trong quá trình huấn luyện"
    }}
  ]
}}

Hãy tạo {num_questions} câu hỏi ngay bây giờ.
"""

OPEN_ENDED_GENERATION_PROMPT_TEMPLATE = """Dựa vào các nguồn tài liệu sau từ khóa học CS431, hãy tạo {num_questions} câu hỏi tự luận dạng câu trả lời ngắn (Short Answer Questions).

# NGUỒN TÀI LIỆU:

{sources}

---

# YÊU CẦU:

Tạo {num_questions} câu hỏi tự luận với các tiêu chí sau:
1. **Câu trả lời ngắn gọn**: Câu hỏi phải được trả lời bằng 1-2 câu, không phải đoạn văn dài
2. **Tập trung vào khái niệm cốt lõi**: Câu hỏi nên kiểm tra sự hiểu biết về khái niệm chính, không yêu cầu giải thích dài dòng
3. **Câu hỏi cụ thể**: Câu hỏi phải rõ ràng và có thể trả lời trực tiếp, không mơ hồ
4. **Câu trả lời tham khảo**: Bao gồm câu trả lời mẫu ngắn gọn (1-2 câu) thể hiện đáp án mong đợi
5. **Source index**: Bao gồm source_index (số thứ tự của nguồn tài liệu, bắt đầu từ 1) để chỉ định nguồn video
6. **Key points**: Liệt kê 2-3 điểm chính mà câu trả lời nên đề cập (dưới dạng mảng)

**QUAN TRỌNG**: Câu trả lời tham khảo (reference_answer) phải ngắn gọn, chỉ 1-2 câu, không phải đoạn văn dài.

# OUTPUT FORMAT:

Trả về câu hỏi theo định dạng JSON sau:
{{
  "questions": [
    {{
      "question": "Mục đích chính của dropout trong mạng neural là gì?",
      "reference_answer": "Dropout được sử dụng để ngăn chặn overfitting bằng cách tắt ngẫu nhiên một phần neuron trong quá trình huấn luyện. Điều này buộc mạng phải học các đặc trưng mạnh mẽ hơn không phụ thuộc vào các neuron cụ thể.",
      "source_index": 1,
      "key_points": ["Ngăn chặn overfitting", "Tắt ngẫu nhiên neuron", "Học đặc trưng mạnh mẽ"]
    }}
  ]
}}

Hãy tạo {num_questions} câu hỏi ngay bây giờ. Nhớ rằng mỗi câu trả lời tham khảo chỉ nên dài 1-2 câu.
"""

MIXED_GENERATION_PROMPT_TEMPLATE = """Dựa vào các nguồn tài liệu sau từ khóa học CS431, hãy tạo {num_mcq} câu hỏi trắc nghiệm (MCQ) và {num_open} câu hỏi tự luận (Open-ended).

# NGUỒN TÀI LIỆU:

{sources}

---

# YÊU CẦU:

**Đối với câu hỏi trắc nghiệm (MCQ):**
1. Câu hỏi phải rõ ràng và cụ thể
2. Cung cấp đúng 4 lựa chọn A, B, C, D
3. Chỉ có một đáp án đúng
4. Bao gồm source_index (số thứ tự của nguồn tài liệu, bắt đầu từ 1)

**Đối với câu hỏi tự luận (Open-ended - Short Answer):**
1. Câu hỏi yêu cầu câu trả lời ngắn gọn (1-2 câu)
2. Tập trung vào khái niệm cốt lõi, không yêu cầu giải thích dài dòng
3. Bao gồm câu trả lời tham khảo ngắn gọn (1-2 câu)
4. Bao gồm source_index (số thứ tự của nguồn tài liệu, bắt đầu từ 1)
5. Liệt kê 2-3 key points chính

# OUTPUT FORMAT:

Trả về câu hỏi theo định dạng JSON sau:
{{
  "mcq_questions": [
    {{
      "question": "Mục đích chính của... là gì?",
      "options": {{
        "A": "Lựa chọn A",
        "B": "Lựa chọn B",
        "C": "Lựa chọn C",
        "D": "Lựa chọn D"
      }},
      "correct_answer": "A",
      "source_index": 1,
      "explanation": "Giải thích ngắn gọn"
    }}
  ],
  "open_ended_questions": [
    {{
      "question": "Mục đích chính của dropout trong mạng neural là gì?",
      "reference_answer": "Dropout được sử dụng để ngăn chặn overfitting bằng cách tắt ngẫu nhiên một phần neuron trong quá trình huấn luyện.",
      "source_index": 2,
      "key_points": ["Điểm 1", "Điểm 2"]
    }}
  ]
}}

Hãy tạo {num_mcq} câu hỏi trắc nghiệm và {num_open} câu hỏi tự luận ngay bây giờ.
"""

VALIDATE_ANSWER_PROMPT_TEMPLATE = """Bạn đang đánh giá câu trả lời của sinh viên cho một câu hỏi tự luận.

# CÂU HỎI:
{question}

# CÂU TRẢ LỜI THAM KHẢO:
{reference_answer}

# CÁC ĐIỂM CHÍNH CẦN ĐỀ CẬP:
{key_points}

# CÂU TRẢ LỜI CỦA SINH VIÊN:
{student_answer}

---

# YÊU CẦU ĐÁNH GIÁ:

Đánh giá câu trả lời của sinh viên dựa trên:
1. **Độ chính xác**: Câu trả lời có phù hợp với câu trả lời tham khảo không?
2. **Tính đầy đủ**: Câu trả lời có bao gồm các điểm chính không?
3. **Sự hiểu biết**: Câu trả lời có thể hiện sự hiểu biết đúng đắn không?

# OUTPUT FORMAT:

Trả về đánh giá theo định dạng JSON sau:
{{
  "score": 0-100,
  "feedback": "Nhận xét chi tiết về những gì tốt và những gì cần cải thiện",
  "covered_points": ["Điểm 1", "Điểm 2"],
  "missing_points": ["Điểm 3"]
}}
"""

