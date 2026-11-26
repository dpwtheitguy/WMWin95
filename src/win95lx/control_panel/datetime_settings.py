"""Date/time conversion, DST policy and transactional timedate1 backend."""
from dataclasses import dataclass
from datetime import datetime,timezone,timedelta
from pathlib import Path
from zoneinfo import ZoneInfo,ZoneInfoNotFoundError
import subprocess,time,struct,json

# Original-style labels; IANA zones supply current civil-time rules.
ZONES=(
 ('(GMT-12:00) International Date Line West','Etc/GMT+12',-720),
 ('(GMT-11:00) Midway Island, Samoa','Pacific/Pago_Pago',-660),
 ('(GMT-10:00) Hawaii','Pacific/Honolulu',-600),
 ('(GMT-09:00) Alaska','America/Anchorage',-540),
 ('(GMT-08:00) Pacific Time (US & Canada); Tijuana','America/Los_Angeles',-480),
 ('(GMT-07:00) Mountain Time (US & Canada)','America/Denver',-420),
 ('(GMT-07:00) Arizona','America/Phoenix',-420),
 ('(GMT-06:00) Central Time (US & Canada)','America/Chicago',-360),
 ('(GMT-06:00) Mexico City, Tegucigalpa','America/Mexico_City',-360),
 ('(GMT-05:00) Eastern Time (US & Canada)','America/New_York',-300),
 ('(GMT-05:00) Bogota, Lima','America/Bogota',-300),
 ('(GMT-04:00) Atlantic Time (Canada)','America/Halifax',-240),
 ('(GMT-03:30) Newfoundland','America/St_Johns',-210),
 ('(GMT-03:00) Brasilia','America/Sao_Paulo',-180),
 ('(GMT-03:00) Buenos Aires, Georgetown','America/Argentina/Buenos_Aires',-180),
 ('(GMT-02:00) Mid-Atlantic','Etc/GMT+2',-120),
 ('(GMT-01:00) Azores, Cape Verde Islands','Atlantic/Azores',-60),
 ('(GMT) Greenwich Mean Time: Dublin, Edinburgh, London','Europe/London',0),
 ('(GMT) Universal Coordinated Time','Etc/UTC',0),
 ('(GMT) Monrovia, Casablanca','Africa/Casablanca',0),
 ('(GMT+01:00) Amsterdam, Berlin, Rome, Stockholm, Vienna','Europe/Berlin',60),
 ('(GMT+01:00) Paris, Madrid','Europe/Paris',60),
 ('(GMT+02:00) Athens, Helsinki, Istanbul','Europe/Helsinki',120),
 ('(GMT+02:00) Cairo','Africa/Cairo',120),
 ('(GMT+02:00) Harare, Pretoria','Africa/Johannesburg',120),
 ('(GMT+02:00) Jerusalem','Asia/Jerusalem',120),
 ('(GMT+03:00) Moscow, St. Petersburg, Volgograd','Europe/Moscow',180),
 ('(GMT+03:00) Baghdad, Kuwait, Riyadh','Asia/Riyadh',180),
 ('(GMT+03:30) Tehran','Asia/Tehran',210),
 ('(GMT+04:00) Abu Dhabi, Muscat','Asia/Dubai',240),
 ('(GMT+04:30) Kabul','Asia/Kabul',270),
 ('(GMT+05:00) Islamabad, Karachi','Asia/Karachi',300),
 ('(GMT+05:30) Bombay, Calcutta, Madras, New Delhi','Asia/Kolkata',330),
 ('(GMT+06:00) Almaty, Dhaka','Asia/Dhaka',360),
 ('(GMT+07:00) Bangkok, Hanoi, Jakarta','Asia/Bangkok',420),
 ('(GMT+08:00) Beijing, Chongqing, Hong Kong','Asia/Shanghai',480),
 ('(GMT+08:00) Perth','Australia/Perth',480),
 ('(GMT+08:00) Singapore, Taipei','Asia/Singapore',480),
 ('(GMT+09:00) Osaka, Sapporo, Tokyo','Asia/Tokyo',540),
 ('(GMT+09:30) Adelaide','Australia/Adelaide',570),
 ('(GMT+09:30) Darwin','Australia/Darwin',570),
 ('(GMT+10:00) Brisbane','Australia/Brisbane',600),
 ('(GMT+10:00) Canberra, Melbourne, Sydney','Australia/Sydney',600),
 ('(GMT+10:00) Guam, Port Moresby','Pacific/Port_Moresby',600),
 ('(GMT+11:00) Magadan, Solomon Islands, New Caledonia','Pacific/Noumea',660),
 ('(GMT+12:00) Auckland, Wellington','Pacific/Auckland',720),
 ('(GMT+12:00) Fiji, Kamchatka, Marshall Islands','Pacific/Fiji',720),
)

NATIVE_ZONE_MAP={
 'GMT':('Europe/London',0),'Warsaw':('Europe/Warsaw',60),'Romance':('Europe/Paris',60),
 'W. Europe':('Europe/Berlin',60),'E. Europe':('Europe/Chisinau',120),'Prague Bratislava':('Europe/Prague',60),
 'GFT':('Europe/Helsinki',120),'E. South America':('America/Sao_Paulo',-180),'Atlantic':('America/Halifax',-240),
 'Eastern':('America/New_York',-300),'Central':('America/Chicago',-360),'Mountain':('America/Denver',-420),
 'Pacific':('America/Los_Angeles',-480),'Alaskan':('America/Anchorage',-540),'Hawaiian':('Pacific/Honolulu',-600),
 'Samoa':('Pacific/Pago_Pago',-660),'New Zealand':('Pacific/Auckland',720),'AUS Eastern':('Australia/Sydney',600),
 'Cen. Australia':('Australia/Adelaide',570),'Tokyo':('Asia/Tokyo',540),'Taipei':('Asia/Taipei',480),
 'Bangkok':('Asia/Bangkok',420),'India':('Asia/Kolkata',330),'Arabian':('Asia/Dubai',240),
 'Iran':('Asia/Tehran',210),'Saudi Arabia':('Asia/Riyadh',180),'Israel':('Asia/Jerusalem',120),
 'Newfoundland':('America/St_Johns',-210),'Azores':('Atlantic/Azores',-60),'Mid-Atlantic':('Etc/GMT+2',-120),
 'Greenwich':('Africa/Casablanca',0),'SA Eastern':('America/Argentina/Buenos_Aires',-180),
 'SA Western':('America/Caracas',-240),'US Eastern':('America/Indiana/Indianapolis',-300),
 'SA Pacific':('America/Bogota',-300),'Canada Central':('America/Regina',-360),'Mexico':('America/Mexico_City',-360),
 'US Mountain':('America/Phoenix',-420),'Dateline':('Etc/GMT+12',-720),'Fiji':('Pacific/Fiji',720),
 'Central Pacific':('Pacific/Guadalcanal',660),'Tasmania':('Australia/Hobart',600),
 'West Pacific':('Pacific/Port_Moresby',600),'AUS Central':('Australia/Darwin',570),
 'Beijing':('Asia/Shanghai',480),'Central Asia':('Asia/Dhaka',360),'West Asia':('Asia/Karachi',300),
 'Afghanistan':('Asia/Kabul',270),'Egypt':('Africa/Cairo',120),'South Africa':('Africa/Johannesburg',120),
 'Russian':('Europe/Moscow',180),'E. Australia':('Australia/Brisbane',600),
}
_existing={zone for label,zone,offset in ZONES}
ZONES+=tuple((zone,zone,offset) for zone,offset in NATIVE_ZONE_MAP.values() if zone not in _existing)

def native_zone_catalog(assets):
    data=json.loads((assets/'native-timezones.json').read_text())
    rows=tuple((row['display'],row['zone'],row['offset']) for row in data['zones'])
    if len(rows)!=52 or any((zone,offset) not in NATIVE_ZONE_MAP.values() for label,zone,offset in rows):raise ValueError('Invalid native time-zone catalog.')
    return rows

def fixed_zone_name(minutes):
    if type(minutes) is not int or not -720<=minutes<=840:raise ValueError('Invalid fixed time-zone offset')
    return 'Win95LX/UTC'+('+' if minutes>=0 else '-')+f'{abs(minutes)//60:02}{abs(minutes)%60:02}'

def fixed_tzif(minutes):
    name=fixed_zone_name(minutes).split('/')[-1].encode()+b'\0'
    return b'TZif\0'+b'\0'*15+struct.pack('>6I',0,0,0,0,1,len(name))+struct.pack('>lBB',minutes*60,0,0)+name

@dataclass(frozen=True)
class DateTimePreferences:
    zone:str='America/Los_Angeles'
    daylight:bool=True
    def validate(self):
        if not isinstance(self.zone,str) or not 1<=len(self.zone)<=100:raise ValueError('Unknown time zone.')
        try:ZoneInfo(self.zone)
        except (ValueError,ZoneInfoNotFoundError) as error:raise ValueError('Unknown time zone.') from error
        if type(self.daylight) is not bool:raise ValueError('Invalid daylight-saving preference.')
        return self
    @property
    def offset(self):
        known=next((offset for label,zone,offset in ZONES if zone==self.zone),None)
        if known is not None:return known
        sample=datetime.now(ZoneInfo(self.zone));return int((sample.utcoffset()-sample.dst()).total_seconds()/60)
    @property
    def system_zone(self):return self.zone if self.daylight else fixed_zone_name(self.offset)
    @property
    def tzinfo(self):return ZoneInfo(self.zone) if self.daylight else timezone(timedelta(minutes=self.offset))

def wall_timestamp(value,prefs):
    """Reject a spring-forward gap instead of silently setting another time."""
    if not isinstance(value,datetime) or value.tzinfo is not None:raise ValueError('Enter a local date and time.')
    aware=value.replace(tzinfo=prefs.tzinfo)
    if datetime.fromtimestamp(aware.timestamp(),prefs.tzinfo).replace(tzinfo=None)!=value:raise ValueError('That local time does not exist because of a daylight-saving change.')
    return aware.timestamp()

class TimedateBackend:
    def __init__(self,runner=None):self.run=runner or self._run
    @staticmethod
    def _run(*args):return subprocess.run(args,check=True,capture_output=True,text=True,timeout=12).stdout
    def snapshot(self):
        text=self.run('timedatectl','show','--property=Timezone','--property=NTP')
        props=dict(line.split('=',1) for line in text.splitlines() if '=' in line)
        return (props.get('Timezone','UTC'),props.get('NTP','no')=='yes',time.time(),time.monotonic())
    def preferences(self):
        zone=self.snapshot()[0]
        if zone=='UTC':zone='Etc/UTC'
        if zone in {key for label,key,offset in ZONES}:return DateTimePreferences(zone)
        for label,key,offset in ZONES:
            if zone==fixed_zone_name(offset):return DateTimePreferences(key,False)
        return DateTimePreferences(zone).validate()
    def apply(self,prefs,edited=None):
        prefs.validate();before=self.snapshot()
        if prefs.system_zone!=before[0]:self.run('timedatectl','--no-ask-password','set-timezone',prefs.system_zone)
        if edited is not None:
            timestamp=wall_timestamp(edited,prefs)
            if before[1]:self.run('timedatectl','--no-ask-password','set-ntp','false')
            self.run('timedatectl','--no-ask-password','set-time',datetime.fromtimestamp(timestamp,prefs.tzinfo).strftime('%Y-%m-%d %H:%M:%S'))
        if self.snapshot()[0]!=prefs.system_zone:raise RuntimeError('The system did not accept the time zone.')
    def restore(self,state):
        zone,ntp,instant,elapsed=state
        self.run('timedatectl','--no-ask-password','set-timezone',zone)
        # Restore the clock only if it was explicitly changed, avoiding
        # needless privileged writes for an ordinary preference failure.
        if abs(time.time()-(instant+time.monotonic()-elapsed))>2:
            self.run('timedatectl','--no-ask-password','set-ntp','false')
            local=datetime.fromtimestamp(instant+time.monotonic()-elapsed,ZoneInfo(zone))
            self.run('timedatectl','--no-ask-password','set-time',local.strftime('%Y-%m-%d %H:%M:%S'))
        self.run('timedatectl','--no-ask-password','set-ntp','true' if ntp else 'false')

class DateTimeController:
    def __init__(self,path,backend):
        self.path,self.backend=path,backend;self.applied=backend.preferences();self.pending=self.applied;self.edited=None
        if path.exists():
            try:self.applied=self.pending=DateTimePreferences(**json.loads(path.read_text())).validate()
            except (OSError,ValueError,TypeError):pass
    def cancel(self):self.pending=self.applied;self.edited=None
    def apply(self):
        from win95lx.control_panel.preferences import save_preferences
        self.pending.validate();before=self.backend.snapshot()
        try:self.backend.apply(self.pending,self.edited);save_preferences(self.pending,self.path)
        except Exception:self.backend.restore(before);raise
        self.applied=self.pending;self.edited=None
        time.tzset()
