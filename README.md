# Nuke Code Editor (CodeEditor_v02)

PySide2 tabanlı, Foundry Nuke içine gömülü bir Python IDE / code editor eklentisi.

## Özellikler
- Çoklu sekmeli editör ve proje/workspace görünümü
- Çıktı/console paneli ile hızlı test ve debug
- Nuke odaklı yardımcılar (node oluşturma, completion vb.)

## Kurulum
1. Bu repodaki `CodeEditor_v02` klasörünü Nuke user dizinine kopyalayın:
   - Windows: `C:\Users\<user>\.nuke\`
   - macOS: `~/Library/Application Support/Foundry/Nuke/` (bazı kurulumlarda `~/.nuke/`)
   - Linux: `~/.nuke/`
2. Nuke user dizininizdeki `init.py` dosyasına aşağıdaki hook’u ekleyin (yoksa oluşturun):

```python
# CodeEditor_v02 init hook
import nuke, os
nuke.pluginAddPath(os.path.join(os.path.dirname(__file__), "CodeEditor_v02"))
```

## Çalıştırma
- Nuke’yi yeniden başlatın.
- Menüden: `Nuke > Python > Python IDE > Open as Window` (veya `Open as Panel`)

## Kaldırma (Uninstall)
- Nuke user dizininizden `CodeEditor_v02` klasörünü kaldırın.
- `init.py` / `menu.py` içine eklediğiniz hook satırlarını silin.

## Bağış Linki (Opsiyonel)
`Donate...` menü öğesini etkinleştirmek için:
- `editor/donate.py` içinde `DONATE_URL` ayarlayın (dağıtım için önerilir), veya
- Ortam değişkeni: `CODEEDITOR_V02_DONATE_URL`, veya
- Kullanıcı `settings.json` içine `General.donate_url`

## Lisans
Apache-2.0: `LICENSE`. Üçüncü parti bağımlılıklar kendi lisanslarıyla gelir (bkz. `third_party/`).

