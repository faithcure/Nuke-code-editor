# Nuke Code Editor (CodeEditor_v02)

PySide2 tabanlı, Foundry Nuke içine gömülü bir Python IDE / code editor eklentisi.

> [!IMPORTANT]
> Bu eklenti **sadece Windows** üzerinde test edilmiştir. macOS/Linux platformlarında **test edilmemiştir**.

---

## ✨ Özellikler
- ⚡ **Nuke içinde IDE deneyimi:** Ayrı uygulama açmadan Nuke içinde kod yaz, çalıştır ve çıktı/traceback’i anında gör
- 🧩 **Node Creator Pro:** Node ara, knob’ları düzenle, **hazır Python kodu üret** (favoriler + filtreleme ile)
- ✍️ **Akıllı editör:** Pygments ile syntax highlighting, auto-completion, kod katlama, satır numaraları, indent yardımcıları
- ▶️ **Çalıştırma seçenekleri:** Seçili kodu veya tüm dosyayı çalıştır; Output/Console üzerinden hızlı deneme
- 🗂️ **Proje akışı:** Proje klasörü aç/oluştur, sekmelerle dosya yönetimi, recent projects
- 🌐 **GitHub menüsü:** Commit / pull / push / status işlemleri IDE içinden
- ⚙️ **Ayarlar:** Autosave, tab size, kısayollar ve davranış ayarları (kullanıcı bazlı)

---

## ⚙️ Kurulum
1. Bu repodaki `CodeEditor_v02` klasörünü Nuke user dizinine kopyalayın:
   - 🪟 Windows: `C:\Users\<user>\.nuke\`
   - 🍎 macOS: `~/Library/Application Support/Foundry/Nuke/` (bazı kurulumlarda `~/.nuke/`)
   - 🐧 Linux: `~/.nuke/`
2. Nuke user dizininizdeki `init.py` dosyasına aşağıdaki hook’u ekleyin (yoksa oluşturun):

```python
# CodeEditor_v02 init hook
import nuke, os
nuke.pluginAddPath(os.path.join(os.path.dirname(__file__), "CodeEditor_v02"))
```

---

## 🚀 Çalıştırma
- Nuke’yi yeniden başlatın.
- Menüden: `Nuke > Python > Python IDE > Open as Window` (veya `Open as Panel`)

---

## 🧹 Kaldırma (Uninstall)
- Nuke user dizininizden `CodeEditor_v02` klasörünü kaldırın.
- `init.py` / `menu.py` içine eklediğiniz hook satırlarını silin.

---

## 🐞 Hata Bildirimi / İstek
Görülen hatalar, öneriler ve özellik istekleri için: https://github.com/faithcure/Nuke-code-editor/issues

---

## 👤 İletişim
- 🌍 Web: https://www.fatihunal.net
- ✉️ E-posta: fatihunal@gmail.com
- 🎬 IMDb: https://www.imdb.com/name/nm10028691/?ref_=nv_sr_srsg_1_tt_0_nm_6_q_fatih%2520%25C3%25BCnal
- 💼 LinkedIn: https://www.linkedin.com/in/fatih-mehmet-unal/

---

## 💝 Bağış Linki (Opsiyonel)
`Donate...` menü öğesini etkinleştirmek için:
- `editor/donate.py` içinde `DONATE_URL` ayarlayın (dağıtım için önerilir), veya
- Ortam değişkeni: `CODEEDITOR_V02_DONATE_URL`, veya
- Kullanıcı `settings.json` içine `General.donate_url`

---

## 🧾 Lisans
Apache-2.0: `LICENSE`. Üçüncü parti bağımlılıklar kendi lisanslarıyla gelir (bkz. `third_party/`).
