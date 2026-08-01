# Contributing

Issues and pull requests are welcome. Keep changes small, explain the user-facing behavior, and never commit credentials or copied quota responses.

Before opening a pull request, run:

```bash
python3 -m py_compile server.py
python3 -m unittest discover -s tests
bash -n install.sh bin/ai-usage-check scripts/install_widget.sh uninstall.sh
node --input-type=module --check < scripts/scriptable_widget.js
node --input-type=module --check < scripts/scriptable_loader.js
```

Provider usage endpoints are undocumented and may change. When changing parsing logic, include sanitized fixture data or a test that does not require a real account.
