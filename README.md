# قالب مشروع Android

يُستخدم كـ**Template** عند إنشاء أي مستودع جديد: GitHub → New repository → Repository template → اختر هذا المستودع.

## ما يأتي جاهزاً
- **`unpack-zip.yml`** — رفع أي `.zip` في الجذر يُفكّ ويُكوَّم تلقائياً.
- **`build.yml`** — بناء APK على كل push، وتوقيع ونشر Release تلقائي إذا أضفت أسرار التوقيع.

## أسرار التوقيع (اختياري)
في Settings → Secrets and variables → Actions:
- `KEYSTORE_BASE64`
- `SIGNING_STORE_PASSWORD`
- `SIGNING_KEY_ALIAS`
- `SIGNING_KEY_PASSWORD`

بدونها: APK يُبنى بمفتاح مؤقت فقط، بلا Release.

## الاستخدام
1. أنشئ مستودعاً جديداً من هذا القالب.
2. ارفع ملف `.zip` لمشروعك (من الهاتف أو أي مكان) في الجذر.
3. انتظر — يُفكّ، يُكوَّم، يُبنى، يُنشر تلقائياً.
