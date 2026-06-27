@echo off

call workon musoyevschool

cd /d C:\Users\user\Desktop\IT-Center-Shofirkon\


start cmd /k "py manage.py runserver"

timeout /t 3 >nul

start chrome http://127.0.0.1:8000/