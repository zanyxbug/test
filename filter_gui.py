import sys
import re
import unicodedata
import pandas as pd
from PyQt6.QtWidgets import (
    QApplication,
    QMainWindow,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QPushButton,
    QLabel,
    QLineEdit,
    QMessageBox,
    QFileDialog,
    QSizePolicy,
    QDialog,
)
from PyQt6.QtCore import Qt

# --- تنظیم رمز عبور ---
APP_PASSWORD = "euler5267"
CREATOR_TAG = " | creator zanko"

# --- نگاشت اعداد فارسی به انگلیسی ---
PERSIAN_TO_ENGLISH_NUMBERS = {
    "۰": "0",
    "۱": "1",
    "۲": "2",
    "۳": "3",
    "۴": "4",
    "۵": "5",
    "۶": "6",
    "۷": "7",
    "۸": "8",
    "۹": "9",
}


def normalize_numbers(text: str) -> str:
    if not isinstance(text, str):
        text = str(text) if pd.notna(text) else ""
    return "".join(PERSIAN_TO_ENGLISH_NUMBERS.get(ch, ch) for ch in text)


# نرمال‌سازی قوی برای حذف کاراکترهای مزاحم و یکسان‌سازی اشکال حروف
# هدف: یکسان شدن «آموزش» و «اموزش» و حذف نیم‌فاصله و مشابه‌ها

def normalize_text(text: str) -> str:
    if not isinstance(text, str):
        text = str(text) if pd.notna(text) else ""

    # نرمال‌سازی یونی‌کد
    text = unicodedata.normalize("NFKC", text)

    # یکسان‌سازی حروف عربی/فارسی و شکل‌های متفاوت
    translation_map = str.maketrans(
        {
            "ي": "ی",
            "ك": "ک",
            "أ": "ا",
            "إ": "ا",
            "آ": "ا",  # آ -> ا تا «آموزش» و «اموزش» همسان شود
            "ة": "ه",
            "ۀ": "ه",
            "ؤ": "و",
            "ئ": "ی",
        }
    )
    text = text.translate(translation_map)

    # تبدیل اعداد فارسی به انگلیسی
    text = normalize_numbers(text)

    # حذف کاراکترهای جهت‌دهی و نیم‌فاصله و مشابه (ZWNJ, LRM, ...)
    text = re.sub(r"[\u200c-\u200f\u202a-\u202e\u2066-\u2069]", " ", text)

    # حذف کنترل‌های ASCII
    text = "".join(ch for ch in text if ord(ch) >= 32)

    # اجازه فقط به حروف محدودهٔ عربی/فارسی، اعداد و فاصله
    text = re.sub(r"[^\u0600-\u06FF0-9\s]+", " ", text)

    # یکسان‌سازی فاصله و حروف کوچک
    text = re.sub(r"\s+", " ", text).strip().lower()

    return text


# ---------------------------------------------------------------------
# پنجره‌ی ورود رمز عبور
# ---------------------------------------------------------------------
class PasswordDialog(QDialog):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("ورود به سامانه" + CREATOR_TAG)
        self.setGeometry(300, 300, 300, 120)
        self.setLayoutDirection(Qt.LayoutDirection.RightToLeft)

        layout = QVBoxLayout(self)
        label = QLabel("لطفاً رمز عبور را وارد کنید:")
        layout.addWidget(label)

        self.password_input = QLineEdit()
        self.password_input.setEchoMode(QLineEdit.EchoMode.Password)
        layout.addWidget(self.password_input)

        btn_layout = QHBoxLayout()
        btn_ok = QPushButton("ورود")
        btn_ok.clicked.connect(self.check_password)
        btn_cancel = QPushButton("خروج")
        btn_cancel.clicked.connect(self.reject)
        btn_layout.addWidget(btn_ok)
        btn_layout.addWidget(btn_cancel)
        layout.addLayout(btn_layout)

    def check_password(self) -> None:
        entered = self.password_input.text().strip()
        if entered == APP_PASSWORD:
            self.accept()
        else:
            QMessageBox.critical(self, "خطا", "❌ رمز عبور نادرست است.")


# ---------------------------------------------------------------------
# پنجره اصلی
# ---------------------------------------------------------------------
class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("سامانه فیلترینگ داده‌ها" + CREATOR_TAG)
        self.setGeometry(100, 100, 380, 160)
        self.setLayoutDirection(Qt.LayoutDirection.RightToLeft)

        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)

        btn_ravansar = QPushButton("مرکز روانسر")
        btn_ravansar.clicked.connect(self.open_ravansar)
        layout.addWidget(btn_ravansar)

        btn_kermanshah = QPushButton("مرکز کرمانشاه")
        btn_kermanshah.clicked.connect(self.open_kermanshah)
        layout.addWidget(btn_kermanshah)

        self.ravansar_win: FilterWindow | None = None
        self.kermanshah_win: FilterWindow | None = None

    def open_ravansar(self) -> None:
        if self.ravansar_win is None or not self.ravansar_win.isVisible():
            self.ravansar_win = FilterWindow("مرکز روانسر" + CREATOR_TAG, need_semester=True)
        self.ravansar_win.show()

    def open_kermanshah(self) -> None:
        if self.kermanshah_win is None or not self.kermanshah_win.isVisible():
            # کلمات کلیدی مجاز برای مرکز کرمانشاه
            allowed_keywords = {
                "آموزش و پرورش ابتدایی": ["آموزش", "پرورش", "ابتدایی"],
                "مدیریت بازرگانی": ["مدیریت", "بازرگانی"],
                "تربیت بدنی": ["تربیت", "بدنی"],
            }

            self.kermanshah_win = FilterWindow(
                "مرکز کرمانشاه" + CREATOR_TAG,
                need_semester=True,
                allowed_majors_keywords=allowed_keywords,
            )
        self.kermanshah_win.show()


# ---------------------------------------------------------------------
# کلاس فیلتر داده‌ها
# ---------------------------------------------------------------------
class FilterWindow(QWidget):
    def __init__(self, title: str, need_semester: bool = True, allowed_majors_keywords: dict | None = None) -> None:
        super().__init__()
        self.setWindowTitle(title)
        self.setGeometry(200, 200, 600, 320)
        self.setLayoutDirection(Qt.LayoutDirection.RightToLeft)

        self.df: pd.DataFrame | None = None
        self.df_filtered: pd.DataFrame | None = None
        self.need_semester = need_semester
        self.allowed_majors_keywords = allowed_majors_keywords

        self.setup_ui()

    def setup_ui(self) -> None:
        main_layout = QVBoxLayout(self)

        file_layout = QHBoxLayout()
        self.file_status_label = QLabel("فایلی بارگذاری نشده است.")
        self.file_status_label.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred
        )
        btn_load = QPushButton("۱. انتخاب فایل اکسل/CSV")
        btn_load.clicked.connect(self.load_file_action)
        file_layout.addWidget(self.file_status_label)
        file_layout.addWidget(btn_load)
        main_layout.addLayout(file_layout)

        if self.need_semester:
            sem_layout = QHBoxLayout()
            sem_label = QLabel("۲. نیم‌سال خود را وارد کنید (مثال: ۴۰۴۱ یا 4041):")
            self.entry_semester = QLineEdit()
            self.entry_semester.setAlignment(Qt.AlignmentFlag.AlignRight)
            sem_layout.addWidget(sem_label)
            sem_layout.addWidget(self.entry_semester)
            main_layout.addLayout(sem_layout)
        else:
            self.entry_semester = None

        btn_apply = QPushButton("۳. اعمال فیلتر")
        btn_apply.clicked.connect(self.apply_filter)
        main_layout.addWidget(btn_apply)

        self.filter_status_label = QLabel("فیلتری اعمال نشده است.")
        main_layout.addWidget(self.filter_status_label)

        btn_save = QPushButton("۴. ذخیره نتیجه فیلتر شده")
        btn_save.clicked.connect(self.save_file_action)
        btn_save.setStyleSheet("background-color: lightgreen;")
        main_layout.addWidget(btn_save)

    def load_file_action(self) -> None:
        filepath, _ = QFileDialog.getOpenFileName(
            self, "انتخاب فایل", "", "Data Files (*.xlsx *.xls *.csv);;All Files (*)"
        )
        if not filepath:
            return
        try:
            if filepath.lower().endswith(".csv"):
                # تلاش برای خواندن با utf-8، سپس windows-1256 (برای فارسی)
                try:
                    self.df = pd.read_csv(filepath, encoding="utf-8")
                except Exception:
                    self.df = pd.read_csv(filepath, encoding="windows-1256", engine="python")
            else:
                self.df = pd.read_excel(filepath)
            self.file_status_label.setText(f"✅ فایل بارگذاری شد. سطرها: {len(self.df)}")
        except Exception as e:
            QMessageBox.critical(self, "خطا", f"❌ خطا در خواندن فایل: {e}")
            self.file_status_label.setText("❌ خطا در بارگذاری فایل!")
            self.df = None

    def save_file_action(self) -> None:
        if self.df_filtered is None or self.df_filtered.empty:
            QMessageBox.warning(
                self,
                "هشدار",
                "⚠️ دیتا فریمی برای ذخیره وجود ندارد. ابتدا فیلتر را اعمال کنید.",
            )
            return
        filepath, _ = QFileDialog.getSaveFileName(
            self, "ذخیره فایل", "", "Excel File (*.xlsx);;CSV File (*.csv)"
        )
        if not filepath:
            return
        try:
            if filepath.lower().endswith(".csv"):
                self.df_filtered.to_csv(filepath, index=False, encoding="utf-8-sig")
            else:
                self.df_filtered.to_excel(filepath, index=False)
            QMessageBox.information(self, "موفقیت", "✅ فایل با موفقیت ذخیره شد.")
        except Exception as e:
            QMessageBox.critical(self, "خطا", f"❌ خطا در ذخیره فایل: {e}")

    def apply_filter(self) -> None:
        if self.df is None:
            QMessageBox.critical(self, "خطا", "لطفاً ابتدا فایل را بارگذاری کنید.")
            return

        SEMESTER_COLUMN = "نیم سال پذیرش"
        DEGREE_COLUMN = "مقطع"
        MAJOR_COLUMN = "رشته"

        if self.need_semester:
            raw_semester = self.entry_semester.text().strip() if self.entry_semester else ""
            normalized_input_semester = normalize_text(raw_semester)
            if not normalized_input_semester:
                QMessageBox.warning(self, "هشدار", "لطفاً نیم‌سال را وارد کنید.")
                return
        else:
            normalized_input_semester = None

        try:
            df = self.df.copy()

            # اطمینان از وجود ستون مقطع
            if DEGREE_COLUMN not in df.columns:
                raise KeyError(DEGREE_COLUMN)

            # ۱. فیلتر مقطع: حذف کارشناسی ارشد، دکتری و موارد ناپیوسته
            exclude_patterns = r"(ارشد|کارشناسی\s*ارشد|دکتری|phd|ناپیوسته|تخصصی)"
            mask_keep_degree = ~df[DEGREE_COLUMN].astype(str).str.contains(
                exclude_patterns, na=False, case=False, regex=True
            )
            df_filtered = df[mask_keep_degree].copy()

            # ۲. فیلتر نیم‌سال (در صورت نیاز)
            if normalized_input_semester is not None:
                if SEMESTER_COLUMN not in df_filtered.columns:
                    raise KeyError(SEMESTER_COLUMN)
                normalized_sem_col = df_filtered[SEMESTER_COLUMN].astype(str).apply(normalize_text)
                mask_sem = normalized_sem_col == normalized_input_semester
                df_filtered = df_filtered[mask_sem]

            # ۳. فیلتر رشته بر اساس کلمات کلیدی (همه کلمات باید وجود داشته باشند)
            if self.allowed_majors_keywords is not None:
                if MAJOR_COLUMN not in df_filtered.columns:
                    raise KeyError(MAJOR_COLUMN)

                normalized_major_col = df_filtered[MAJOR_COLUMN].astype(str).apply(normalize_text)

                mask_major = pd.Series(False, index=df_filtered.index)
                for required_words in self.allowed_majors_keywords.values():
                    normalized_words = [normalize_text(word) for word in required_words]
                    current_mask = normalized_major_col.apply(
                        lambda s: all(word in s for word in normalized_words)
                    )
                    mask_major = mask_major | current_mask

                df_filtered = df_filtered[mask_major]

            self.df_filtered = df_filtered.reset_index(drop=True)
            self.filter_status_label.setText(
                f"✅ فیلتر اعمال شد. ردیف نهایی: {len(self.df_filtered)}"
            )

        except KeyError as e:
            QMessageBox.critical(self, "خطا", f"❌ ستون مورد نظر یافت نشد: {e}")
        except Exception as e:
            QMessageBox.critical(self, "خطا", f"❌ خطای نامشخص: {e}")


# ---------------------------------------------------------------------
# اجرای برنامه
# ---------------------------------------------------------------------
if __name__ == "__main__":
    app = QApplication(sys.argv)
    login = PasswordDialog()
    if login.exec() == QDialog.DialogCode.Accepted:
        window = MainWindow()
        window.show()
        sys.exit(app.exec())
    else:
        sys.exit()
