echo Starting work flow
python3 define_app.py
echo Defined Balsam App
python3 define_jobs.py
echo Creating Balsam jobs
sleep 120
echo Building dot file
python3 build_dot_file.py

