from __future__ import annotations

import io
import json
import re
import subprocess
import sys
from pathlib import Path

import pandas as pd
import streamlit as st

from database import (DB_PATH, get_predictions, list_prediction_batches, list_training_runs,
                      record_prediction_batch, record_training_run)

ROOT = Path(__file__).resolve().parent
TRAIN_ROOT = ROOT.parent / '01_TRAIN_MODEL'
OUTPUT = TRAIN_TRAIN_ROOT / 'outputs'
MAX_UPLOAD_MB = 100
MAX_UPLOAD_BYTES = MAX_UPLOAD_MB * 1024 * 1024
TASK = 'binary'

st.set_page_config(page_title='TextSense | Phân loại văn bản', page_icon='🧠', layout='wide')
st.title('🧠 TextSense — Phân loại văn bản mạng xã hội')
st.caption('Xây dựng hệ thống phân loại nhị phân văn bản mạng xã hội dựa trên phân tích cảm xúc bằng học máy.')
st.info(f'Giới hạn tải CSV: tối đa {MAX_UPLOAD_MB} MB mỗi tệp. Lịch sử chạy và dự đoán được lưu trong SQLite cục bộ: `{DB_PATH.relative_to(ROOT)}`.')

with st.sidebar:
    st.header('⚙️ Cấu hình')
    task = TASK
    st.caption('Bài toán cố định: phân loại nhị phân theo quy ước proxy của đồ án.')
    max_features = st.select_slider('Số đặc trưng TF-IDF tối đa', options=[10000, 20000, 40000, 60000], value=40000)
    bootstrap = st.select_slider('Số lần bootstrap CI', options=[100, 300, 500, 1000], value=500)
    st.caption('Mô hình nhị phân dùng quy ước proxy: 1 = Phản cảm; 0 = Không phản cảm. Chỉ dùng TF-IDF + LinearSVC; C chọn bằng 5-fold CV theo AP, ngưỡng chọn trên validation.')
    st.code('01_TRAIN_MODEL/do_an_textsense_v3.ipynb', language='text')

train_tab, predict_tab, results_tab, history_tab, guide_tab = st.tabs(
    ['🚀 Huấn luyện', '🔎 Dự đoán', '📊 Kết quả', '🗃️ SQL / Lịch sử', '📘 Hướng dẫn'])

with train_tab:
    st.subheader('Huấn luyện mô hình bằng Jupyter Notebook')
    st.info('Mở `01_TRAIN_MODEL/do_an_textsense_v3.ipynb` trong VS Code rồi chạy các cell từ trên xuống. Cả Twitter_Data.csv và Reddit_Data.csv đều được sử dụng.')
    twitter = TRAIN_ROOT / 'data' / 'Twitter_Data.csv'
    reddit = TRAIN_ROOT / 'data' / 'Reddit_Data.csv'
    c1, c2 = st.columns(2)
    c1.metric('Twitter_Data.csv', 'Đã có' if twitter.exists() else 'Thiếu')
    c2.metric('Reddit_Data.csv', 'Đã có' if reddit.exists() else 'Thiếu')
    model_file = OUTPUT / 'binary_linear_svm.joblib'
    st.metric('Mô hình LinearSVC', 'Đã huấn luyện' if model_file.exists() else 'Chưa huấn luyện')
    st.caption('Nhãn proxy: -1 → 1 Phản cảm; 0/1 → 0 Không phản cảm. SQL Server chỉ dùng cho lưu trữ và phân tích tùy chọn.')

with predict_tab:
    st.subheader('Dự đoán văn bản')
    model_task = 'binary'
    st.caption('TextSense hiện chỉ cung cấp mô hình nhị phân proxy: Phản cảm / Không phản cảm.')
    model_path = OUTPUT / f'{model_task}_linear_svm.joblib'
    if not model_path.exists():
        st.warning('Chưa có model. Hãy huấn luyện trước.')
    st.caption('Tên nhãn proxy: 1 = Phản cảm · 0 = Không phản cảm. Đây là ánh xạ từ nhãn cảm xúc, không phải xác minh nội dung thực sự phản cảm.')
    text_input = st.text_area('Nhập văn bản tiếng Anh', height=130, placeholder='Enter a tweet or comment...')
    if st.button('Phân tích văn bản'):
        if not model_path.exists():
            st.error('Chưa tìm thấy model đã huấn luyện.')
        elif not text_input.strip():
            st.warning('Hãy nhập văn bản trước.')
        else:
            try:
                from predict import predict
                result = predict(model_path, [text_input])
                st.dataframe(pd.DataFrame(result), width='stretch')
                record_prediction_batch(model_task, 'manual_input', result, len(text_input.encode('utf-8')),
                                        text_input.encode('utf-8'))
            except Exception as exc:
                st.exception(exc)
    st.divider()
    st.markdown(f'**Dự đoán hàng loạt từ CSV (tối đa {MAX_UPLOAD_MB} MB)**')
    uploaded = st.file_uploader('Tải CSV có cột văn bản tên `text`', type=['csv'], key='prediction_csv')
    if uploaded is not None:
        if uploaded.size > MAX_UPLOAD_BYTES:
            st.error(f'Tệp vượt giới hạn {MAX_UPLOAD_MB} MB. Tệp hiện tại: {uploaded.size / 1024 / 1024:.1f} MB.')
        else:
            st.caption(f'{uploaded.name} · {uploaded.size / 1024 / 1024:.2f} MB')
            if st.button('Dự đoán file CSV'):
                if not model_path.exists():
                    st.error('Chưa có model tương ứng.')
                else:
                    try:
                        raw = uploaded.getvalue()
                        frame = pd.read_csv(io.BytesIO(raw))
                        if 'text' not in frame.columns:
                            st.error('CSV cần có cột `text`.')
                        else:
                            from predict import predict
                            result = predict(model_path, frame['text'].fillna('').astype(str).tolist())
                            result_frame = pd.DataFrame(result)
                            st.dataframe(result_frame.head(100), width='stretch')
                            st.download_button('Tải kết quả CSV', result_frame.to_csv(index=False).encode('utf-8-sig'),
                                               file_name='textsense_predictions.csv', mime='text/csv')
                            batch_id = record_prediction_batch(model_task, uploaded.name, result,
                                                               uploaded.size, raw)
                            st.success(f'Đã lưu {len(result):,} kết quả vào SQLite. Batch ID: {batch_id}')
                    except Exception as exc:
                        st.exception(exc)

with results_tab:
    st.subheader('Báo cáo đánh giá từ lần train gần nhất')
    metric_files = sorted(OUTPUT.glob('*_metrics.json'), key=lambda p: p.stat().st_mtime, reverse=True) if OUTPUT.exists() else []
    if not metric_files:
        st.info('Chưa có báo cáo. Chạy huấn luyện trước.')
    else:
        selected = st.selectbox('Chọn báo cáo', metric_files, format_func=lambda p: p.name)
        report = json.loads(selected.read_text(encoding='utf-8'))
        st.markdown('**Thống kê mô tả dữ liệu đã làm sạch**')
        summary_file = OUTPUT / 'binary_data_summary.csv'
        if summary_file.exists():
            st.dataframe(pd.read_csv(summary_file), width='stretch')
        descriptive_images = [
            ('binary_source_distribution.png', 'Số lượng văn bản theo nguồn'),
            ('binary_original_label_distribution.png', 'Phân bố nhãn cảm xúc gốc'),
            ('binary_label_distribution.png', 'Phân bố nhãn nhị phân proxy'),
            ('binary_text_length_distribution.png', 'Phân bố độ dài văn bản'),
            ('binary_top20_terms.png', '20 từ phổ biến nhất')
        ]
        existing_descriptive = [(name, caption) for name, caption in descriptive_images if (OUTPUT / name).exists()]
        if existing_descriptive:
            st.markdown('**Biểu đồ thống kê mô tả**')
            for name, caption in existing_descriptive:
                st.image(str(OUTPUT / name), caption=caption, width='stretch')
        st.markdown('**So sánh mô hình trên cùng tập dữ liệu**')
        comparison_file = OUTPUT / 'binary_model_comparison.csv'
        if comparison_file.exists():
            st.dataframe(pd.read_csv(comparison_file), width='stretch')
        else:
            st.info('Chưa có bảng baseline. Chạy do_an_textsense_v3.ipynb để tạo so sánh Naive Bayes và LinearSVC.')
        a, b, c = st.columns(3)
        a.metric('Accuracy', f"{report.get('accuracy', 0):.4f}")
        b.metric('Macro F1', f"{report.get('f1_macro', 0):.4f}")
        c.metric('Test samples', f"{report.get('test_rows', 0):,}")
        st.markdown('**Classification report**')
        st.dataframe(pd.DataFrame(report.get('classification_report', {})).T, width='stretch')
        st.markdown('**Confusion matrix**')
        st.dataframe(pd.DataFrame(report.get('confusion_matrix', [])), width='stretch')
        cm_image = OUTPUT / 'binary_confusion_matrix.png'
        if cm_image.exists():
            st.image(str(cm_image), caption='Confusion Matrix trên tập test', width='stretch')
        if 'decision' in report:
            st.markdown('**So sánh ngưỡng mặc định và ngưỡng chọn từ validation**')
            st.write('Ngưỡng validation:', report['decision']['validation_selected_threshold'])
            st.dataframe(pd.DataFrame([
                {'Ngưỡng': '0 mặc định', **report['decision']['test_threshold_0']},
                {'Ngưỡng': 'Validation', **report['decision']['test_threshold_selected']}
            ]), width='stretch')
            st.caption('Mô hình chính: TF-IDF + LinearSVC; baseline đối chứng: Multinomial Naive Bayes. C được chọn bằng Stratified 5-fold CV theo Average Precision trên tập train.')
            st.markdown('**Bảng chọn C qua 5-fold CV — average precision (AP), không phải F1**')
            cv_file = OUTPUT / 'binary_cv_results.csv'
            if cv_file.exists():
                st.dataframe(pd.read_csv(cv_file), width='stretch')
            st.markdown('**Đường cong Precision–Recall và phân tích lỗi**')
            pr_image = OUTPUT / report.get('diagnostics', {}).get('pr_curve_png', 'binary_pr_curve.png')
            if pr_image.exists():
                st.image(str(pr_image), caption='Precision–Recall curve trên tập test')
            diagnostics = report.get('diagnostics', {})
            error_file = OUTPUT / diagnostics.get('error_analysis_csv', 'binary_error_analysis.csv')
            if error_file.exists():
                st.caption(f"Số mẫu dự đoán sai: {diagnostics.get('misclassified_rows', 0):,} · FN: {diagnostics.get('false_negative_rows', 0):,} · FP: {diagnostics.get('false_positive_rows', 0):,}")
                st.dataframe(pd.read_csv(error_file).head(100), width='stretch')
            feature_file = OUTPUT / diagnostics.get('feature_importance_csv', 'binary_feature_importance.csv')
            if feature_file.exists():
                st.markdown('**Đặc trưng TF-IDF có hệ số lớn nhất**')
                st.dataframe(pd.read_csv(feature_file), width='stretch')
            st.write('Bootstrap 95% CI F1 lớp 1:', report.get('test_bootstrap_95pct_f1_1'))
            st.markdown('**Theo nguồn dữ liệu**')
            st.json(report.get('by_source', {}))
            st.markdown('**Theo độ dài văn bản**')
            st.json(report.get('by_length', {}))
            st.markdown('**Theo nhãn cảm xúc gốc**')
            st.json(report.get('by_original_sentiment', {}))
            st.markdown('**Hash dữ liệu và tập chia**')
            st.json({'data_hashes': report.get('data_hashes'), 'split_file_sha256': report.get('split_file_sha256')})
        st.download_button('Tải JSON báo cáo', selected.read_bytes(), file_name=selected.name, mime='application/json')

with history_tab:
    st.subheader('Lịch sử lưu trong SQLite')
    runs = list_training_runs()
    if runs:
        display_runs = [{k: row.get(k) for k in ('id', 'started_utc', 'task', 'status', 'model_path')} for row in runs]
        st.markdown('**Lịch sử huấn luyện**')
        st.dataframe(pd.DataFrame(display_runs), width='stretch')
    else:
        st.info('Chưa có lần huấn luyện nào được lưu.')
    batches = list_prediction_batches()
    if batches:
        st.markdown('**Lịch sử dự đoán / tệp tải lên**')
        st.dataframe(pd.DataFrame(batches), width='stretch')
        batch_ids = [row['id'] for row in batches]
        selected_batch = st.selectbox('Xem chi tiết batch', batch_ids)
        history_frame = pd.DataFrame(get_predictions(selected_batch)).head(500)
        if not history_frame.empty and 'predicted_label' in history_frame.columns:
            history_frame['label_name'] = history_frame['predicted_label'].map({0: 'Không phản cảm', 1: 'Phản cảm'}).fillna('')
        st.dataframe(history_frame, width='stretch')
    else:
        st.info('Chưa có batch dự đoán nào được lưu.')
    st.caption('Cơ sở dữ liệu SQLite được lưu cục bộ. Có thể mở bằng DB Browser for SQLite hoặc công cụ SQLite trong VS Code.')

with guide_tab:
    st.subheader('Cài đặt và sử dụng trong VS Code')
    st.markdown('''
1. Mở thư mục dự án trong VS Code.
2. Cài extension **Python** và **Jupyter**.
3. Tạo môi trường và cài dependencies:
''')
    st.code('py -3 -m venv .venv\n.\\.venv\\Scripts\\python.exe -m pip install -r requirements.txt\n.\\.venv\\Scripts\\python.exe -m pip install -r requirements-app.txt', language='powershell')
    st.markdown('4. Chạy giao diện web:')
    st.code('.\\.venv\\Scripts\\python.exe -m streamlit run app.py', language='powershell')
    st.markdown('5. Notebook `do_an_textsense_v3.ipynb` vẫn được giữ nguyên trong dự án; mở bằng VS Code Jupyter để thao tác từng cell như Colab.')
    st.markdown('6. TextSense dùng một mô hình TF-IDF + LinearSVC và hai nguồn dữ liệu Twitter, Reddit. Nhãn đầu ra là quy ước proxy ánh xạ từ nhãn cảm xúc gốc; không phải nhãn phản cảm được xác minh độc lập.')
