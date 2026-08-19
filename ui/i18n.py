from __future__ import annotations

from typing import Callable

_CURRENT_LANG = "ar"
_LISTENERS: list[Callable[[str], None]] = []

# English source text -> Arabic UI text. Technical identifiers remain unchanged.
_AR = {
    "Ready":"جاهز","Dashboard":"لوحة المعلومات","Import":"استيراد","CRS Converter":"محول أنظمة الإحداثيات","Survey Tools":"أدوات المساحة","Civil / CAD":"مدني / CAD","Batch Converter":"التحويل الجماعي","Map":"الخريطة","History":"السجل","Settings":"الإعدادات","About":"حول البرنامج",
    "MH GeoSuite Pro":"MH GeoSuite Pro","Professional Surveying & Geospatial Engineering Suite":"منظومة احترافية للمساحة والهندسة الجغرافية المكانية",
    "Scan Project Folder":"فحص مجلد المشروع","Refresh":"تحديث","Use Selected File":"استخدام الملف المحدد","Ready — select a project folder to inspect it.":"جاهز — اختر مجلد المشروع لفحص محتوياته.",
    "FILES FOUND":"الملفات المكتشفة","FORMATS":"التنسيقات","ACTIVE FILE":"الملف النشط","CRS ENGINE":"محرك الإحداثيات","Supported coordinate files":"ملفات الإحداثيات المدعومة","File types detected":"أنواع الملفات المكتشفة","Current workspace file":"ملف مساحة العمل الحالي","Global CRS database":"قاعدة بيانات أنظمة الإحداثيات العالمية",
    "Project Files — click a row to select it, then Use Selected File":"ملفات المشروع — اضغط على صف لتحديده ثم استخدم الملف المحدد","File":"الملف","Format":"التنسيق","Size":"الحجم","Modified":"آخر تعديل","Path":"المسار",
    "SOURCE FILE":"الملف المصدر","SOURCE CRS":"نظام الإحداثيات المصدر","TARGET CRS":"نظام الإحداثيات الهدف","CONVERT":"تحويل","Total Points":"إجمالي النقاط","Successful":"ناجح","Failed":"فاشل","Warnings":"تحذيرات",
    "Choose File":"اختيار ملف","Choose Folder":"اختيار مجلد","Choose Files":"اختيار ملفات","Open Coordinate File":"فتح ملف إحداثيات","Reload Selected":"إعادة تحميل المحدد","Background":"الخلفية","Show Labels":"إظهار التسميات","FIT ALL POINTS":"إظهار جميع النقاط","Point Size":"حجم النقطة","Label Size":"حجم التسمية","Light":"فاتح","Dark":"داكن",
    "ZIGZAG / GRID ORDERING":"ترتيب Zigzag / الشبكة","Ordering":"الترتيب","Ordering Method":"طريقة الترتيب","Group":"المجموعة","Start":"البداية","North-West":"شمال غرب","North-East":"شمال شرق","Reverse Each Row":"عكس كل صف","Auto Detect Grid":"اكتشاف الشبكة تلقائيًا","Source Order":"ترتيب المصدر","Point Code / Name":"كود / اسم النقطة","All Points":"كل النقاط","Zigzag (Start West)":"Zigzag (البداية من الغرب)","Zigzag (Start East)":"Zigzag (البداية من الشرق)","Keep Source Order":"الإبقاء على ترتيب المصدر",
    "Language / اللغة:":"اللغة:","Theme / المظهر:":"المظهر:","Decimal Precision:":"الدقة العشرية:","English":"الإنجليزية","العربية":"العربية","Dark / داكن":"داكن","Light / فاتح":"فاتح","Auto / تلقائي":"تلقائي",
    "Theme and language changes are applied immediately. Decimal precision is persisted for all pages that use current_precision().":"يتم تطبيق تغييرات اللغة والمظهر فورًا، ويتم حفظ الدقة العشرية لجميع الصفحات.",
    "Load CAD File":"تحميل ملف CAD","Load Excel (.XLSX)":"تحميل Excel (.XLSX)","Load CSV (.CSV)":"تحميل CSV (.CSV)","Load Survey TXT (.TXT)":"تحميل ملف المساحة (.TXT)","No file selected":"لم يتم اختيار ملف","Loaded 0 points | Invalid 0":"تم تحميل 0 نقطة | غير صالح 0","points loaded":"نقطة محملة","No coordinate points were detected in the selected file.":"لم يتم العثور على نقاط إحداثيات في الملف المحدد.",
    "Point / Survey Code":"النقطة / كود المساحة","X":"X","Y":"Y","Z":"Z","Name":"الاسم","Src X":"X المصدر","Src Y":"Y المصدر","Src Z":"Z المصدر","Tgt X":"X الهدف","Tgt Y":"Y الهدف","Tgt Z":"Z الهدف","Status":"الحالة","Message":"الرسالة",
    "MAP — SURVEY POINT PREVIEW":"الخريطة — معاينة نقاط المساحة","MAP DISPLAY CONTROLS":"عناصر التحكم بالخريطة","MAP VIEW — ALL LOADED POINTS":"الخريطة — جميع النقاط المحملة","Civil / CAD Converter":"محول Civil / CAD","RESET":"إعادة ضبط",
    "Convert survey points to CAD (DXF) or Civil 3D (CSV)":"تحويل نقاط المساحة إلى CAD (DXF) أو Civil 3D (CSV)","Smart Parsing, Axis Control and independent Grid/Zigzag ordering.":"تحليل ذكي، والتحكم في المحاور، وترتيب مستقل للشبكة وZigzag.","DIRECT CAD EXPORT — use loaded coordinates exactly as they are (NO CRS conversion)":"تصدير CAD مباشر — استخدام الإحداثيات كما هي دون تحويل CRS",
    "FILE PARSING OPTIONS":"خيارات تحليل الملف","Smart (Recommended)":"ذكي (موصى به)","Manual / Select Columns":"يدوي / اختيار الأعمدة","Parsing Engine":"محرك التحليل","Detected Format":"التنسيق المكتشف","Easting / X":"الشرقي / X","Northing / Y":"الشمالي / Y","Elevation / Z (optional)":"المنسوب / Z (اختياري)","Point Code / Name (optional)":"كود / اسم النقطة (اختياري)",
    "Choose the correct columns above, then click PREVIEW to apply the changes to the table.":"اختر الأعمدة الصحيحة أعلاه ثم اضغط معاينة لتطبيق التغييرات على الجدول.","PREVIEW":"معاينة","Preview":"معاينة","Preview Again":"معاينة مرة أخرى","Export DXF":"تصدير DXF","Export Civil 3D CSV":"تصدير CSV لـ Civil 3D",
    "AXIS ORDER — IMPORTANT":"ترتيب المحاور — مهم","Easting (X) → Northing (Y)  |  Standard (Recommended)":"الشرقي (X) ← الشمالي (Y) | قياسي (موصى به)","Northing (Y) → Easting (X)  |  SWAP":"الشمالي (Y) ← الشرقي (X) | تبديل","The selected axis order is applied to the PREVIEW table when you click PREVIEW.":"يتم تطبيق ترتيب المحاور المحدد على جدول المعاينة عند الضغط على معاينة.",
    "GRID / ZIGZAG POINT NUMBERING":"ترقيم النقاط بالشبكة / Zigzag","Group by Point Code / Name":"التجميع حسب كود / اسم النقطة","Row tolerance (m)":"سماحية الصف (م)","COORDINATE REFERENCE SYSTEM":"نظام الإحداثيات المرجعي","CRS conversion is performed only by CONVERT & PREPARE. PREVIEW shows parsing/axis/ordering changes before conversion.":"يتم تحويل CRS فقط بواسطة تحويل وتجهيز. المعاينة تعرض تغييرات التحليل والمحاور والترتيب قبل التحويل.","POINTS PREVIEW TABLE":"جدول معاينة النقاط","Preview is up to date":"المعاينة محدثة","Displayed:":"المعروض:","Invalid:":"غير صالح:","CONVERT & PREPARE FOR CAD / CIVIL 3D":"تحويل وتجهيز لـ CAD / Civil 3D","EXPORT DXF":"تصدير DXF","EXPORT CIVIL 3D CSV":"تصدير Civil 3D CSV",
    "Export Converted Points":"تصدير النقاط المحولة","AutoCAD / Civil 3D — DXF":"AutoCAD / Civil 3D — DXF","Civil 3D — PENZD CSV":"Civil 3D — PENZD CSV","Excel XLSX":"Excel XLSX","Generic CSV":"CSV عام","Survey TXT":"ملف المساحة TXT",
    "No coordinate file loaded":"لم يتم تحميل ملف إحداثيات","Open / Change File":"فتح / تغيير الملف","Column Mapping":"مطابقة الأعمدة","Point Name / Survey Code →":"اسم النقطة / كود المساحة ←","X / Easting / Longitude →":"X / الشرقي / خط الطول ←","Y / Northing / Latitude →":"Y / الشمالي / خط العرض ←","Z / Elevation →":"Z / المنسوب ←","<none>":"<بدون>",
    "Search CRS: WGS 84, EPSG:4326, UTM, Ain el Abd, Amanah Riyadh...":"ابحث عن نظام إحداثيات: WGS 84، EPSG:4326، UTM، عين العبد، أمانة الرياض...","No CRS selected":"لم يتم اختيار نظام إحداثيات","Search":"بحث","Select":"اختيار","CRS":"نظام الإحداثيات",
    "SURVEY TOOLS — COGO / FIELD CALCULATIONS":"أدوات المساحة — COGO / الحسابات الحقلية","1  TWO-POINT INVERSE / COGO":"1  العكس بين نقطتين / COGO","POINT 1":"النقطة 1","POINT 2":"النقطة 2","CALCULATE INVERSE":"حساب العكس","2  CALCULATION RESULTS":"2  نتائج الحساب","Horizontal Distance":"المسافة الأفقية","Slope Distance":"المسافة المائلة","Azimuth":"السمت","Bearing":"الاتجاه","Grade":"الانحدار","3  POLYGON AREA":"3  مساحة المضلع","CALCULATE AREA":"حساب المساحة","Area: —":"المساحة: —","Invalid Input":"إدخال غير صالح","Invalid Polygon":"مضلع غير صالح","Enter valid numeric coordinates for both points.":"أدخل إحداثيات رقمية صحيحة لكلتا النقطتين.","Enter 3 or more vertices as X,Y pairs.":"أدخل 3 رؤوس أو أكثر على شكل أزواج X,Y.",
    "MH GeoSuite Pro — Batch Converter":"MH GeoSuite Pro — التحويل الجماعي","Use Active File":"استخدام الملف النشط","Refresh Scan":"تحديث الفحص","No folder/files selected":"لم يتم اختيار مجلد/ملفات","Workspace: no project folder":"مساحة العمل: لا يوجد مجلد مشروع","Project Workspace":"مساحة عمل المشروع","READY":"جاهز","Scan Error":"خطأ في الفحص","No Project Folder":"لا يوجد مجلد مشروع","No files":"لا توجد ملفات","No supported coordinate files selected.":"لم يتم اختيار ملفات إحداثيات مدعومة.","No CRS":"لا يوجد نظام إحداثيات","Select both Source CRS and Target CRS.":"اختر نظام الإحداثيات المصدر والهدف.","Batch complete":"اكتمل التحويل الجماعي",
    "History — Conversion Log":"السجل — سجل التحويلات","Load Selected File":"تحميل الملف المحدد","Open File Folder":"فتح مجلد الملف","Clear History":"مسح السجل","Date/Time":"التاريخ/الوقت","Source File":"الملف المصدر","Target CRS":"نظام الإحداثيات الهدف","Points":"النقاط","File Not Found":"الملف غير موجود","History Error":"خطأ في السجل","Open Folder":"فتح المجلد","Version":"الإصدار","License":"الترخيص","Commercial":"تجاري","Open LinkedIn Profile":"فتح ملف LinkedIn","Check for Updates":"التحقق من التحديثات","Update Available":"يتوفر تحديث","Update Failed":"فشل التحديث","Update Error":"خطأ في التحديث","You are using the latest available version.":"أنت تستخدم أحدث إصدار متاح.","Update installation is available in the Windows standalone version.":"تثبيت التحديثات متاح في إصدار Windows المستقل.","Developed by Mahmoud Hemida":"تم التطوير بواسطة محمود حميدة","Support / Contact":"الدعم / التواصل","UI Framework":"إطار واجهة المستخدم","CRS Engine":"محرك أنظمة الإحداثيات",
    "Nothing to export":"لا توجد بيانات للتصدير","Run the conversion first.":"قم بتنفيذ التحويل أولًا.","Export Complete":"اكتمل التصدير","Exported":"تم التصدير","Transformation Error":"خطأ في التحويل","Import Error":"خطأ في الاستيراد","Coordinate File Error":"خطأ في ملف الإحداثيات","DXF Export Error":"خطأ في تصدير DXF","Civil 3D Export Error":"خطأ في تصدير Civil 3D","TXT Export Error":"خطأ في تصدير TXT","No data":"لا توجد بيانات","Please choose a source file first.":"اختر ملف المصدر أولًا.","Saved to":"تم الحفظ في","DXF created successfully":"تم إنشاء DXF بنجاح","Civil 3D PENZD point file created":"تم إنشاء ملف نقاط Civil 3D PENZD","TXT created successfully":"تم إنشاء TXT بنجاح",
    "Selected file":"الملف المحدد","Active File":"الملف النشط","Project Folder":"مجلد المشروع","shared workspace":"مساحة عمل مشتركة","PROJECT WORKSPACE":"مساحة عمل المشروع","Shared across all pages":"مشترك بين جميع الصفحات","PROJECT WORKSPACE: Not selected — choose a folder once from Dashboard":"مساحة عمل المشروع: لم يتم الاختيار — اختر مجلدًا مرة واحدة من لوحة المعلومات","History file loaded":"تم تحميل ملف السجل","ready for further editing/conversion":"جاهز لمزيد من التعديل/التحويل","Batch result ready for CAD/Civil 3D":"نتيجة التحويل الجماعي جاهزة لـ CAD/Civil 3D",
}

_TRANSLATIONS = {"ar": _AR, "en": {key: key for key in _AR}}


def register_language_listener(callback: Callable[[str], None]) -> None:
    if callback not in _LISTENERS:
        _LISTENERS.append(callback)


def set_language(lang: str) -> None:
    global _CURRENT_LANG
    _CURRENT_LANG = lang if lang in ("ar", "en") else "ar"
    for callback in tuple(_LISTENERS):
        try:
            callback(_CURRENT_LANG)
        except Exception:
            pass


def current_language() -> str:
    return _CURRENT_LANG


def tr(text: str) -> str:
    return _AR.get(text, text) if _CURRENT_LANG == "ar" else text
