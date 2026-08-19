import streamlit as st
import pandas as pd
from supabase import create_client, Client
from datetime import datetime, date

# =========================================================
# Branch Transfers V2
# Requires Supabase tables from schema.sql
# =========================================================

st.set_page_config(
    page_title="نظام تحويلات الفروع",
    page_icon="📦",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Cairo:wght@400;600;700&display=swap');
html, body, .stApp, p, h1, h2, h3, h4, h5, h6, label, input, textarea, button,
[data-testid="stMarkdownContainer"], [data-testid="stDataFrame"] {
    font-family: 'Cairo', Tahoma, Arial, sans-serif !important;
}
.stMarkdown, p, h1, h2, h3, h4, label {
    direction: rtl !important;
    text-align: right !important;
}
.metric-card {
    padding: 14px;
    border-radius: 12px;
    border: 1px solid #ddd;
    background: #fff;
}
.status-pending {color:#b26a00;font-weight:700}
.status-received {color:#087f5b;font-weight:700}
.status-cancelled {color:#c92a2a;font-weight:700}
</style>
""", unsafe_allow_html=True)

SUPABASE_URL = st.secrets.get("SUPABASE_URL", "")
SUPABASE_KEY = st.secrets.get("SUPABASE_KEY", "")

if not SUPABASE_URL or not SUPABASE_KEY:
    st.error("بيانات Supabase غير موجودة في Streamlit Secrets.")
    st.stop()

@st.cache_resource
def get_supabase(url: str, key: str) -> Client:
    return create_client(url, key)

supabase = get_supabase(SUPABASE_URL, SUPABASE_KEY)

BRANCHES = ["دمياط", "المعادي", "المطار", "الجلاء", "المهندسين"]
ROLES = ["admin", "manager", "employee"]

def db_error(e):
    st.error(f"حدث خطأ في قاعدة البيانات: {e}")

def login():
    st.markdown(
        '<div class="main-header"><h1>📦 نظام تحويلات الفروع</h1></div>',
        unsafe_allow_html=True,
    )
    st.markdown(
        "<p style='text-align:center'>تسجيل الدخول — V2.2</p>",
        unsafe_allow_html=True,
    )

    with st.form("login_form", clear_on_submit=False):
        username = st.text_input("اسم المستخدم", placeholder="اكتب اسم المستخدم")
        password = st.text_input("كلمة المرور", type="password", placeholder="اكتب كلمة المرور")
        submitted = st.form_submit_button("دخول", use_container_width=True, type="primary")

    if not submitted:
        return

    username_clean = str(username).strip()
    password_clean = str(password).strip()

    if not username_clean or not password_clean:
        st.error("⚠️ أدخل اسم المستخدم وكلمة المرور.")
        return

    try:
        # ابحث باسم المستخدم فقط أولاً، حتى نعرف هل Streamlit يرى الحساب أصلًا.
        response = (
            supabase.table("app_users")
            .select("id, username, password, full_name, branch, role, is_active")
            .eq("username", username_clean)
            .limit(1)
            .execute()
        )
        
st.write("🔧 DEBUG:", response.data)
        users = response.data or []

        if not users:
            st.error("❌ اسم المستخدم غير موجود في قاعدة البيانات.")
            with st.expander("🔧 تشخيص الاتصال"):
                st.write("النسخة الحالية: V2.2")
                st.write("اسم المستخدم المرسل:", repr(username_clean))
                st.write("عدد النتائج:", len(users))
                st.info(
                    "إذا كان admin موجودًا في Supabase، فغالبًا Streamlit متصل "
                    "بمشروع Supabase مختلف أو أن مفتاح الاتصال لا يطابق المشروع."
                )
            return

        db_user = users[0]

        if not db_user.get("is_active"):
            st.error("❌ المستخدم موجود ولكن الحساب غير نشط.")
            return

        stored_password = str(db_user.get("password", "")).strip()

        if stored_password != password_clean:
            st.error("❌ اسم المستخدم أو كلمة المرور غير صحيحة.")
            with st.expander("🔧 معلومات التشخيص"):
                st.write("النسخة الحالية: V2.2")
                st.write("اسم المستخدم الموجود:", db_user.get("username"))
                st.write("الحساب نشط:", db_user.get("is_active"))
                st.write("طول كلمة المرور المدخلة:", len(password_clean))
                st.write("طول كلمة المرور في قاعدة البيانات:", len(stored_password))
            return

        st.session_state.user = {
            "id": db_user["id"],
            "username": db_user["username"],
            "full_name": db_user["full_name"],
            "branch": db_user["branch"],
            "role": db_user["role"],
            "is_active": db_user["is_active"],
        }
        st.rerun()

    except Exception as e:
        st.error(f"❌ حدث خطأ أثناء تسجيل الدخول: {e}")
        with st.expander("🔧 تفاصيل الخطأ"):
            st.exception(e)

if "user" not in st.session_state:
    login()
    st.stop()

user = st.session_state.user
current_branch = user["branch"]
role = user["role"]

with st.sidebar:
    st.markdown(f"### 👤 {user['full_name']}")
    st.markdown(f"**الفرع:** {current_branch}")
    st.markdown(f"**الصلاحية:** {role}")

    if st.button("🚪 تسجيل الخروج", use_container_width=True):
        st.session_state.clear()
        st.rerun()

    st.divider()
    st.caption("الإصدار V2")

# ---------------------------------------------------------
# Data helpers
# ---------------------------------------------------------
def get_transfers():
    q = supabase.table("transfers").select("*").order("id", desc=True)
    if role != "admin":
        q = q.or_(f"from_branch.eq.{current_branch},target_branch.eq.{current_branch}")
    return q.execute().data or []

def get_products():
    return supabase.table("products").select("*").eq("is_active", True).order("name").execute().data or []

# ---------------------------------------------------------
# Header
# ---------------------------------------------------------
st.markdown(
    f'<div class="main-header"><h1>📦 نظام تحويلات الفروع — {current_branch}</h1></div>',
    unsafe_allow_html=True
)

# ---------------------------------------------------------
# Dashboard
# ---------------------------------------------------------
try:
    transfers = get_transfers()
except Exception as e:
    db_error(e)
    transfers = []

df = pd.DataFrame(transfers)

if not df.empty:
    if role == "admin":
        pending = int((df["status"] == "قيد الانتظار").sum())
        received = int((df["status"] == "تم الاستلام").sum())
        cancelled = int((df["status"] == "ملغي").sum())
    else:
        pending = int(((df["status"] == "قيد الانتظار") & (df["target_branch"] == current_branch)).sum())
        received = int((df["status"] == "تم الاستلام").sum())
        cancelled = int((df["status"] == "ملغي").sum())
else:
    pending = received = cancelled = 0

m1, m2, m3, m4 = st.columns(4)
m1.metric("📦 إجمالي التحويلات", len(df))
m2.metric("⏳ قيد الانتظار", pending)
m3.metric("✅ تم الاستلام", received)
m4.metric("❌ ملغي", cancelled)

tab_send, tab_receive, tab_history, tab_reports = st.tabs(
    ["📤 إرسال تحويل", "📥 الاستلام", "📋 السجل", "📊 التقارير"]
)

# ---------------------------------------------------------
# Send
# ---------------------------------------------------------
with tab_send:
    st.subheader("📤 تسجيل تحويل جديد")

    products = get_products()
    if not products:
        st.warning("لا توجد أصناف في قاعدة البيانات. أضف الأصناف أولًا من Supabase.")
    else:
        product_map = {p["id"]: f'{p["name"]} — {p.get("code","")}' for p in products}

        target_options = [b for b in BRANCHES if b != current_branch]
        target = st.selectbox("الفرع المستلم", target_options)
        transfer_date = st.date_input("تاريخ التحويل", value=date.today())
        sender = st.text_input("اسم القائم بالتحويل", value=user["full_name"])
        notes = st.text_area("ملاحظات")

        st.markdown("### الأصناف")
        item_rows = []

        for i in range(10):
            c1, c2, c3 = st.columns([5, 2, 2])
            with c1:
                pid = st.selectbox(
                    f"الصنف {i+1}",
                    [None] + list(product_map.keys()),
                    format_func=lambda x: "— اختر صنفًا —" if x is None else product_map[x],
                    key=f"pid_{i}",
                )
            with c2:
                qty = st.number_input(f"الكمية {i+1}", min_value=0.0, step=1.0, key=f"qty_{i}")
            with c3:
                if pid is not None:
                    st.write(f"الكود: {next((p.get('code','') for p in products if p['id']==pid), '')}")
            if pid is not None and qty > 0:
                item_rows.append({"product_id": pid, "quantity": qty})

        if st.button("🚀 إرسال التحويلة", type="primary", use_container_width=True):
            if not sender.strip():
                st.error("اكتب اسم الموظف القائم بالتحويل.")
            elif not item_rows:
                st.error("أضف صنفًا واحدًا على الأقل بكمية أكبر من صفر.")
            else:
                try:
                    # Generate readable transfer number
                    stamp = datetime.now().strftime("%Y%m%d%H%M%S")
                    transfer_code = f"TR-{stamp}"

                    transfer = {
                        "from_branch": current_branch,
                        "target_branch": target,
                        "transfer_date": str(transfer_date),
                        "transfer_code": transfer_code,
                        "sender_name": sender.strip(),
                        "notes": notes.strip(),
                        "status": "قيد الانتظار",
                        "created_by": user["id"],
                    }
                    result = supabase.table("transfers").insert(transfer).execute()
                    transfer_id = result.data[0]["id"]

                    rows = [
                        {
                            "transfer_id": transfer_id,
                            "product_id": x["product_id"],
                            "quantity": x["quantity"],
                        }
                        for x in item_rows
                    ]
                    supabase.table("transfer_items").insert(rows).execute()

                    supabase.table("transfer_logs").insert({
                        "transfer_id": transfer_id,
                        "user_id": user["id"],
                        "action": "إنشاء تحويل",
                        "details": f"تحويل {transfer_code} من {current_branch} إلى {target}",
                    }).execute()

                    st.success(f"تم إنشاء التحويلة {transfer_code} بنجاح.")
                    st.rerun()
                except Exception as e:
                    db_error(e)

# ---------------------------------------------------------
# Receive
# ---------------------------------------------------------
with tab_receive:
    st.subheader(f"📥 التحويلات الواردة إلى {current_branch}")

    incoming = [
        x for x in transfers
        if x.get("target_branch") == current_branch and x.get("status") == "قيد الانتظار"
    ]

    if not incoming:
        st.info("لا توجد تحويلات معلقة حاليًا.")
    else:
        options = {x["id"]: f'{x["transfer_code"]} — من {x["from_branch"]}' for x in incoming}
        selected = st.selectbox(
            "اختر التحويلة",
            list(options.keys()),
            format_func=lambda x: options[x],
        )
        receiver = st.text_input("اسم المستلم", value=user["full_name"])
        receipt_date = st.date_input("تاريخ الاستلام", value=date.today())

        transfer = next(x for x in incoming if x["id"] == selected)

        try:
            items = (supabase.table("transfer_items")
                     .select("*, products(name, code)")
                     .eq("transfer_id", selected)
                     .execute().data or [])
            if items:
                view = pd.DataFrame([{
                    "الصنف": x["products"]["name"] if x.get("products") else "",
                    "الكود": x["products"].get("code","") if x.get("products") else "",
                    "الكمية": x["quantity"],
                } for x in items])
                st.dataframe(view, use_container_width=True, hide_index=True)
        except Exception as e:
            db_error(e)

        if st.button("✅ تأكيد الاستلام", type="primary", use_container_width=True):
            if not receiver.strip():
                st.error("اكتب اسم الموظف المستلم.")
            else:
                try:
                    supabase.table("transfers").update({
                        "receiver_name": receiver.strip(),
                        "receipt_date": str(receipt_date),
                        "status": "تم الاستلام",
                    }).eq("id", selected).execute()

                    supabase.table("transfer_logs").insert({
                        "transfer_id": selected,
                        "user_id": user["id"],
                        "action": "تأكيد استلام",
                        "details": f"تم استلام التحويلة {transfer['transfer_code']}",
                    }).execute()

                    st.success("تم تأكيد الاستلام.")
                    st.rerun()
                except Exception as e:
                    db_error(e)

# ---------------------------------------------------------
# History
# ---------------------------------------------------------
with tab_history:
    st.subheader("📋 سجل التحويلات")

    if df.empty:
        st.info("لا توجد تحويلات.")
    else:
        c1, c2, c3 = st.columns(3)
        search = c1.text_input("🔎 بحث برقم التحويلة")
        status_filter = c2.selectbox("الحالة", ["الكل", "قيد الانتظار", "تم الاستلام", "ملغي"])
        branch_filter = c3.selectbox("الفرع", ["الكل"] + BRANCHES)

        view = df.copy()
        if search:
            view = view[view["transfer_code"].astype(str).str.contains(search, case=False, na=False)]
        if status_filter != "الكل":
            view = view[view["status"] == status_filter]
        if branch_filter != "الكل":
            view = view[
                (view["from_branch"] == branch_filter) |
                (view["target_branch"] == branch_filter)
            ]

        cols = [
            "transfer_code", "from_branch", "target_branch",
            "transfer_date", "sender_name", "status",
            "receipt_date", "receiver_name", "notes"
        ]
        cols = [x for x in cols if x in view.columns]
        labels = {
            "transfer_code":"رقم التحويلة", "from_branch":"من فرع",
            "target_branch":"إلى فرع", "transfer_date":"تاريخ التحويل",
            "sender_name":"القائم بالتحويل", "status":"الحالة",
            "receipt_date":"تاريخ الاستلام", "receiver_name":"المستلم",
            "notes":"ملاحظات"
        }
        st.dataframe(view[cols].rename(columns=labels), use_container_width=True, hide_index=True)

        st.download_button(
            "⬇️ تنزيل Excel/CSV",
            data=view.to_csv(index=False).encode("utf-8-sig"),
            file_name="transfers_report.csv",
            mime="text/csv",
        )

# ---------------------------------------------------------
# Reports
# ---------------------------------------------------------
with tab_reports:
    st.subheader("📊 تقرير التحويلات")

    if df.empty:
        st.info("لا توجد بيانات للتقرير.")
    else:
        by_branch = (
            df.groupby(["from_branch", "target_branch"])
              .size()
              .reset_index(name="عدد التحويلات")
              .sort_values("عدد التحويلات", ascending=False)
        )
        st.dataframe(by_branch, use_container_width=True, hide_index=True)

        st.markdown("### حسب الحالة")
        by_status = df["status"].value_counts().rename_axis("الحالة").reset_index(name="العدد")
        st.bar_chart(by_status.set_index("الحالة"))

# ---------------------------------------------------------
# Admin
# ---------------------------------------------------------
if role == "admin":
    st.sidebar.divider()
    st.sidebar.success("أنت مدير النظام.")
