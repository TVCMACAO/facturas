"""Debug-mode NDJSON logger for agent sessions."""
import json
import os
import time


def agent_log(location, message, data=None, hypothesis_id=None, run_id='pre-fix'):
    # #region agent log
    payload = {
        'sessionId': 'e8ef29',
        'timestamp': int(time.time() * 1000),
        'location': location,
        'message': message,
        'data': data or {},
        'hypothesisId': hypothesis_id,
        'runId': run_id,
    }
    candidates = [
        os.path.join(os.path.dirname(os.path.dirname(__file__)), 'debug-e8ef29.log'),
        os.path.join(os.getcwd(), 'debug-e8ef29.log'),
        '/app/debug-e8ef29.log',
    ]
    line = json.dumps(payload, default=str) + '\n'
    for log_path in candidates:
        try:
            with open(log_path, 'a', encoding='utf-8') as fh:
                fh.write(line)
            break
        except OSError:
            continue
    try:
        from flask import has_app_context, current_app
        if has_app_context():
            current_app.logger.error('AGENT_DEBUG %s', line.strip())
    except Exception:
        pass
    # #endregion
