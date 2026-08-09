import streamlit as st
import pandas as pd
import sqlite3
from datetime import datetime

st.set_page_config(page_title="نظام تحويلات الفروع", layout="wide")

st.title("📦 نظام تسجيل واستلام التحويلات بين الفروع")

DB_FILE = "transfers_db.sqlite"

def init_db():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS transfers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            from_branch TEXT,
            transfer_date TEXT,
            transfer_code TEXT,
            sender_name TEXT,
            target_branch TEXT,
            receiver_name TEXT,
            receipt_date TEXT,
            status TEXT DEFAULT 'قيد الانتظار',
            notes TEXT
        )
    ''')
    conn.commit()
    conn.close()

init_db()

BRANCHES = ["دمياط", "المعادي", "الجلاء", "المطار"]

with st.sidebar:
    current_branch = st.selectbox("اختر الفرع الحالي للجهاز:", BRANCHES)

tab1, tab2, tab3 = st.tabs(["📤 إرسال تحويل", "📥 استلام تحويل", "📊 السجل الشامل"])

with tab1:
    with st.form("new_transfer"):
        col1, col2, col3 = st.columns(3)
        code = col1.text_input("رقم التحويلة")
        sender = col2.text_input("اسم الموظف المرسل")
        target = col3.selectbox("إلى فرع", [b for b in BRANCHES if b != current_branch])
        notes = st.text_area("ملاحظات")
        
        if st.form_submit_button("إرسال التحويلة"):
            if code and sender:
                conn = sqlite3.connect(DB_FILE)
                c = conn.cursor()
                c.execute('''
                    INSERT INTO transfers (from_branch, transfer_date, transfer_code, sender_name, target_branch, notes)
                    VALUES (?, ?, ?, ?, ?, ?)
                ''', (current_branch, str(datetime.today().date()), code, sender, target, notes))
                conn.commit()
                conn.close()
                st.success("تم تسجيل الإرسال بنجاح!")
            else:
                st.error("يرجى ملء البيانات الأساسية!")

with tab2:
    conn = sqlite3.connect(DB_FILE)
    df_in = pd.read_sql_query("SELECT * FROM transfers WHERE target_branch = ? AND status = 'قيد الانتظار'", conn, params=(current_branch,))
    conn.close()
    st.dataframe(df_in, use_container_width=True)

with tab3:
    conn = sqlite3.connect(DB_FILE)
    df_all = pd.read_sql_query("SELECT * FROM transfers ORDER BY id DESC", conn)
    conn.close()
    st.dataframe(df_all, use_container_width=True)
