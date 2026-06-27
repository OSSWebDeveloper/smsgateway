@echo off

call workon musoyevschool

cd /d C:\Users\user\Desktop\IT-Center-Shofirkon\

REM Django serverni ishga tushirish
start cmd /k "py manage.py runserver"

REM Ngrokni ishga tushirish
start cmd /k "ngrok http --url=roughy-outgoing-iguana.ngrok-free.app 8080"

REM Server ochilishi uchun kutish
timeout /t 5 >nul

REM Chrome’da saytni ochish
start chrome http://127.0.0.1:8000/

exit
