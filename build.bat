@echo off
python -m PyInstaller --onefile --windowed --name "TheTallyCounter" --noconfirm tally_counter.py
pause
