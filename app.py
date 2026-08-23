import streamlit as st
import pandas as pd
import datetime
from supabase import create_client, Client

st.set_page_config(page_title="نظام تحويلات الفروع", page_icon="📦", layout="wide")

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Cairo:wght@400;600;700&display=swap');
html,body,.stApp,p,div,label,input,textarea,button{font-family:'Cairo',Tahoma,Arial,sans-serif!important}
.stApp{direction:rtl}
h1,h2,h3,h4,p,label,[data-testid="stMarkdownContainer"]{direction:rtl!important;text-align:right!important}
</style>
""", unsafe_allow_html=True)

@st.cache_resource
def init_supabase(url: str, key: str) -> Client:
    return create_client(url, key)

try:
    supabase = init_supabase(st.secrets["SUPABASE_URL"], st.secrets["SUPABASE_KEY"])
except Exception as e:
    st.error("❌ تعذر الاتصال بـ Supabase")
    st.code(str(e))
    st.stop()

for k, v in {
    "logged_in": False, "username": None, "role": None, "current_branch": None
}.items():
    if k not in st.session_state:
        st.session_state[k] = v

def logout():
    st.session_state.logged_in = False
    st.session_state.username = None
    st.session_state.role = None
    st.session_state.current_branch = None
    st.rerun()

def get_branches():
    r = supabase.table("branches").select("branch_name").order("branch_name").execute()
    return [x["branch_name"] for x in (r.data or [])]

def authenticate(username, password):
    username = username.strip()
    if not username or not password:
        return None, "يرجى إدخال اسم المستخدم وكلمة المرور."
    try:
        r = (supabase.table("app_users")
              .select("id,username,password,role,is_active")
              .eq("username", username)
              .limit(1).execute())
        users = r.data or []
        if not users:
            return None, "اسم المستخدم غير موجود في قاعدة البيانات."
        user = users[0]
        if not user.get("is_active", False):
            return None, "هذا المستخدم غير نشط."
        if str(user.get("password", "")) != password:
            return None, "كلمة المرور غير صحيحة."
        return user, None
    except Exception as e:
        return None, f"حدث خطأ أثناء قراءة app_users: {e}"

# ================= تسجيل الدخول =================
if not st.session_state.logged_in:
    st.markdown('<h1 style="text-align:center!important">🔐 نظام تحويلات الفروع 📦</h1>', unsafe_allow_html=True)
    st.markdown('<p style="text-align:center!important;color:#666">تسجيل الدخول إلى نظام متابعة التحويلات</p>', unsafe_allow_html=True)

    with st.container(border=True):
        st.subheader("تسجيل الدخول")
        username = st.text_input("اسم المستخدم:", placeholder="مثال: admin")
        password = st.text_input("كلمة المرور:", type="password")
        if st.button("دخول", type="primary", use_container_width=True):
            user, err = authenticate(username, password)
            if err:
                st.error(err)
            else:
                st.session_state.logged_in = True
                st.session_state.username = user["username"]
                st.session_state.role = user.get("role", "user")
                st.rerun()
    st.caption("نسخة مطورة تعتمد على جدول app_users.")
    st.stop()

# ================= بعد الدخول =================
try:
    branches = get_branches()
except Exception as e:
    st.error("❌ تعذر تحميل الفروع")
    st.code(str(e))
    st.stop()

if not branches:
    st.error("❌ لا توجد فروع في جدول branches.")
    st.stop()

if st.session_state.current_branch not in branches:
    st.session_state.current_branch = branches[0]

with st.sidebar:
    st.header("⚙️ إعدادات الجهاز")
    st.write(f"👤 المستخدم: **{st.session_state.username}**")
    st.write(f"🔑 الصلاحية: **{st.session_state.role}**")
    st.session_state.current_branch = st.selectbox(
        "📍 الفرع الحالي:", branches,
        index=branches.index(st.session_state.current_branch)
    )
    if st.button("🚪 تسجيل الخروج", use_container_width=True):
        logout()

st.markdown('<h1 style="text-align:center!important">📦 نظام تحويلات الفروع</h1>', unsafe_allow_html=True)
st.info(f"📍 الفرع الحالي: **{st.session_state.current_branch}**  |  👤 المستخدم: **{st.session_state.username}**")

tab1, tab2, tab3 = st.tabs(["📤 إرسال تحويل", "📥 الاستلام", "📜 السجل"])

# ================= إرسال =================
with tab1:
    st.header("📤 تسجيل تحويل جديد")
    others = [b for b in branches if b != st.session_state.current_branch]
    if not others:
        st.warning("لا توجد فروع أخرى.")
    else:
        with st.form("send_transfer", clear_on_submit=True):
            c1, c2 = st.columns(2)
            with c1:
                transfer_num = st.text_input("رقم التحويلة:")
                sender_staff = st.text_input("القائم بالتحويل:")
            with c2:
                receiver_branch = st.selectbox("الفرع المستقبل:", others)
                transfer_date = st.date_input("تاريخ التحويل:", datetime.date.today())
            notes = st.text_area("ملاحظات:")
            submit = st.form_submit_button("🚀 إرسال التحويل", type="primary", use_container_width=True)

            if submit:
                if not transfer_num.strip() or not sender_staff.strip():
                    st.error("يرجى إدخال رقم التحويلة واسم القائم بالتحويل.")
                else:
                    payload = {
                        "transfer_number": transfer_num.strip(),
                        "sender_branch": st.session_state.current_branch,
                        "sender_staff": sender_staff.strip(),
                        "receiver_branch": receiver_branch,
                        "transfer_date": str(transfer_date),
                        "status": "قيد الانتظار",
                        "notes": notes.strip()
                    }
                    try:
                        supabase.table("transfers").insert(payload).execute()
                        st.success(f"✅ تم إرسال التحويلة رقم {transfer_num} إلى {receiver_branch}.")
                        st.rerun()
                    except Exception as e:
                        st.error("❌ حدث خطأ أثناء تسجيل التحويلة.")
                        st.code(str(e))

# ================= الاستلام =================
with tab2:
    st.header("📥 التحويلات الواردة")
    try:
        r = (supabase.table("transfers").select("*")
             .eq("receiver_branch", st.session_state.current_branch)
             .eq("status", "قيد الانتظار")
             .order("id", desc=True).execute())
        pending = r.data or []
    except Exception as e:
        st.error("❌ تعذر تحميل التحويلات.")
        st.code(str(e))
        pending = []

    if not pending:
        st.info("✨ لا توجد تحويلات بانتظار الاستلام.")
    else:
        st.success(f"📦 يوجد {len(pending)} تحويلة بانتظار الاستلام.")
        for item in pending:
            with st.expander(f"📦 تحويلة رقم {item.get('transfer_number','')} — من {item.get('sender_branch','')}"):
                st.write(f"**التاريخ:** {item.get('transfer_date','')}")
                st.write(f"**القائم بالتحويل:** {item.get('sender_staff','')}")
                if item.get("notes"):
                    st.info(f"📝 {item['notes']}")
                with st.form(f"receive_{item['id']}"):
                    receiver_staff = st.text_input("اسم القائم بالاستلام:")
                    confirm = st.form_submit_button("✅ تأكيد الاستلام", type="primary", use_container_width=True)
                    if confirm:
                        if not receiver_staff.strip():
                            st.error("يرجى إدخال اسم القائم بالاستلام.")
                        else:
                            try:
                                supabase.table("transfers").update({
                                    "status": "تم الاستلام",
                                    "receiver_staff": receiver_staff.strip(),
                                    "receipt_date": str(datetime.date.today())
                                }).eq("id", item["id"]).execute()
                                st.success("🎉 تم تأكيد الاستلام.")
                                st.rerun()
                            except Exception as e:
                                st.error("❌ حدث خطأ أثناء تأكيد الاستلام.")
                                st.code(str(e))

# ================= السجل =================
with tab3:
    st.header("📜 سجل التحويلات")
    c1, c2 = st.columns(2)
    with c1:
        status_filter = st.selectbox("الحالة:", ["الكل", "قيد الانتظار", "تم الاستلام"])
    with c2:
        search = st.text_input("🔎 بحث برقم التحويلة:")

    try:
        r = (supabase.table("transfers").select("*")
             .or_(f"sender_branch.eq.{st.session_state.current_branch},receiver_branch.eq.{st.session_state.current_branch}")
             .order("id", desc=True).execute())
        history = r.data or []
    except Exception as e:
        st.error("❌ تعذر تحميل السجل.")
        st.code(str(e))
        history = []

    if status_filter != "الكل":
        history = [x for x in history if x.get("status") == status_filter]
    if search.strip():
        q = search.strip().lower()
        history = [x for x in history if q in str(x.get("transfer_number","")).lower()]

    if history:
        rows = [{
            "رقم التحويلة": x.get("transfer_number",""),
            "من فرع": x.get("sender_branch",""),
            "إلى فرع": x.get("receiver_branch",""),
            "تاريخ التحويل": x.get("transfer_date",""),
            "القائم بالتحويل": x.get("sender_staff",""),
            "الحالة": x.get("status",""),
            "القائم بالاستلام": x.get("receiver_staff",""),
            "تاريخ الاستلام": x.get("receipt_date",""),
            "الملاحظات": x.get("notes","")
        } for x in history]
        st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
        st.caption(f"إجمالي النتائج: {len(rows)}")
    else:
        st.info("لا توجد تحويلات مطابقة.")

with st.expander("🔧 تشخيص الاتصال"):
    st.write("Supabase: ✅ متصل")
    st.write("جدول تسجيل الدخول: `app_users`")
    st.write("المستخدم:", st.session_state.username)
    st.write("الصلاحية:", st.session_state.role)
    st.write("الفرع:", st.session_state.current_branch)
