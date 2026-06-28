import time
import uuid
import json
from ..models import FileResult

class JsonReporter:

    def _serialize(self, results: list[FileResult]) -> list[dict]:
        scan_id = str(uuid.uuid4())
        timestamp = time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())
        events = []
        for r in results:
            breakdown = {'delta_growth': 0, 'iqr': 0, 'keycount': 0, 'entropy': 0, 'string_size': 0, 'consistency': 0, 'cross_repo': 0}
            for check in r.checks:
                c_name = check.check.lower()
                weight = 0
                if check.score >= 2:
                    weight = 12
                elif check.score == 1:
                    weight = 6
                if any((k in c_name for k in ['corpus', 'cross'])):
                    breakdown['cross_repo'] += weight
                elif any((k in c_name for k in ['consist', 'format', 'parse', 'mismatch', 'limit', 'flags', 'error'])):
                    breakdown['consistency'] += weight
                elif any((k in c_name for k in ['entropy', 'randomness'])):
                    breakdown['entropy'] += weight
                elif any((k in c_name for k in ['key', 'array', 'root', 'field'])):
                    breakdown['keycount'] += weight
                elif any((k in c_name for k in ['string', 'token', 'length'])):
                    breakdown['string_size'] += weight
                elif any((k in c_name for k in ['iqr', 'absolute', 'peer', 'stat', 'floor'])):
                    breakdown['iqr'] += weight
                else:
                    breakdown['delta_growth'] += weight
            events.append({'@timestamp': timestamp, 'scan_id': scan_id, 'event_type': 'csg_file_scan', 'severity': r.verdict, 'filepath': str(r.filepath).replace('\\', '/'), 'total_score': r.total_score, 'score': r.total_score, 'triggered_correlations': r.correlations_triggered, 'breakdown': breakdown})
        return events

    def report(self, results: list[FileResult]) -> None:
        events = self._serialize(results)
        for event in events:
            print(json.dumps(event))