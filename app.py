import streamlit as st
import datetime
from supabase import create_client

# الاتصال بـ Supabase
@st.cache_resource
def init_supabase():
    url = st.secrets["SUPABASE_URL"]
    key = st.secrets["SUPABASE_KEY"]
    return create_client(url, key)

supabase = init_supabase()

st.set_page_config(page_title="نظام متابعة التحويلات", page_icon="📦", layout="centered")

# إدارة الجلسة (Session State)
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
if "current_branch" not in st.session_state:
    st.session_state.current_branch = None

# ----------------1. شاشة تسجيل الدخول ----------------
if not st.session_state.logged_in:
    st.title("🔐 تسجيل الدخول - نظام التحويلات")
    
    # جلب قائمة الفروع
    try:
        branches_res = supabase.table("branches").select("branch_name").execute()
        branch_list = [b["branch_name"] for b in branches_res.data] if branches_res.data else []
    except Exception as e:
        st.error(f"خطأ في الاتصال بقاعدة البيانات: {e}")
        branch_list = []

    selected_branch = st.selectbox("اختر الفرع:", branch_list if branch_list else ["لا توجد فروع"])
    password_input = st.text_input("كلمة السر:", type="password")

    if st.button("دخول", use_container_width=True):
        if selected_branch and password_input:
            # التحقق من كلمة السر
            res = supabase.table("branches").select("*").eq("branch_name", selected_branch).eq("password", password_input).execute()
            if res.data:
                st.session_state.logged_in = True
                st.session_state.current_branch = selected_branch
                st.rerun()
            else:
                st.error("كلمة السر غير صحيحة!")
        else:
            st.warning("يرجى اختيار الفرع وإدخال كلمة السر.")

# ----------------2. شاشة التطبيق الرئيسية ----------------
else:
    # شريط أعلى الصفحة
    col_title, col_logout = st.columns([3, 1])
    with col_title:
        st.subheader(f"📍 الفرع الحالي: {st.session_state.current_branch}")
    with col_logout:
        if st.button("تسجيل خروج"):
            st.session_state.logged_in = False
            st.session_state.current_branch = None
            st.rerun()

    st.markdown("---")

    # التبويبات الرئيسية
    tab1, tab2, tab3 = st.tabs(["📤 إرسال تحويل", "📥 الاستلام", "📜 السجل"])

    # ---------------- تبويب 1: إرسال تحويل ----------------
    with tab1:
        st.header("تسجيل تحويل جديد")
        
        # جلب الفروع الأخرى المستقبلة
        all_branches = supabase.table("branches").select("branch_name").execute().data
        other_branches = [b["branch_name"] for b in all_branches if b["branch_name"] != st.session_state.current_branch]

        with st.form("send_transfer_form", clear_on_submit=True):
            transfer_num = st.text_input("رقم التحويلة:")
            sender_staff = st.text_input("القائم بالتحويل (اسم الموظف):")
            receiver_branch = st.selectbox("الفرع المستقبل:", other_branches)
            transfer_date = st.date_input("التاريخ:", datetime.date.today())
            
            submit_btn = st.form_submit_button("إرسال التحويل", use_container_width=True)

            if submit_btn:
                if transfer_num and sender_staff and receiver_branch:
                    payload = {
                        "transfer_number": transfer_num,
                        "sender_branch": st.session_state.current_branch,
                        "sender_staff": sender_staff,
                        "receiver_branch": receiver_branch,
                        "transfer_date": str(transfer_date),
                        "status": "قيد الانتظار"
                    }
                    supabase.table("transfers").insert(payload).execute()
                    st.success("تم تسجيل التحويل بنجاح! 🚀")
                else:
                    st.error("يرجى ملء جميع الحقول المطلوبة.")

    # ---------------- تبويب 2: استلام تحويل ----------------
    with tab2:
        st.header("التحويلات الواردة للفرع")
        
        # جلب التحويلات الموجهة لهذا الفرع والتي لا تزال "قيد الانتظار"
        pending_res = supabase.table("transfers").select("*")\
            .eq("receiver_branch", st.session_state.current_branch)\
            .eq("status", "قيد الانتظار")\
            .execute()

        pending_transfers = pending_res.data

        if not pending_transfers:
            st.info("لا توجد تحويلات بانتظار الاستلام حالياً.")
        else:
            for item in pending_transfers:
                with st.expander(f"📦 تحويلة رقم: {item['transfer_number']} - من فرع: {item['sender_branch']}"):
                    st.write(f"**التاريخ:** {item['transfer_date']}")
                    st.write(f"**القائم بالتحويل:** {item['sender_staff']}")
                    
                    with st.form(f"receive_form_{item['id']}"):
                        receiver_staff = st.text_input("اسم القائم بالاستلام:")
                        confirm_btn = st.form_submit_button("تأكيد الاستلام ✅")

                        if confirm_btn:
                            if receiver_staff:
                                supabase.table("transfers").update({
                                    "status": "تم الاستلام",
                                    "receiver_staff": receiver_staff
                                }).eq("id", item["id"]).execute()
                                
                                st.success("تم تأكيد الاستلام بنجاح!")
                                st.rerun()
                            else:
                                st.error("يرجى إدخال اسم القائم بالاستلام.")

    # ---------------- تبويب 3: السجل والتقارير ----------------
    with tab3:
        st.header("سجل التحويلات")
        
        # جلب كافة التحويلات الخاصة بهذا الفرع (سواء كمرسل أو كمستقبل)
        history_res = supabase.table("transfers").select("*")\
            .or_(f"sender_branch.eq.{st.session_state.current_branch},receiver_branch.eq.{st.session_state.current_branch}")\
            .order("id", desc=True)\
            .execute()

        if history_res.data:
            st.dataframe(history_res.data, use_container_width=True)
        else:
            st.info("لا توجد تحويلات مسجلة بعد.")
