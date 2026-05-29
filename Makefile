.PHONY: install run test clean-outputs

install:
	pip install -r requirements.txt

run:
	streamlit run app.py

test:
	pytest

clean-outputs:
	powershell -NoProfile -Command "Get-ChildItem outputs -File -Include *.xlsx,*.log,*.md,*.docx | Remove-Item -Force"
