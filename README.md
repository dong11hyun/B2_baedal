## 실행 방법

python -m venv venv

venv\Scripts\activate # 또는 source venv/bin/activate

pip install -r requirements.txt

- settings.py 에서 postgresql 비밀번호 입력 필수!

python manage.py migrate

python manage.py createsuperuser

python manage.py runserver

python attack.py  <서버를 실행 후에 코드 실행해야함>
