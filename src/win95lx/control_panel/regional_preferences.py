"""Per-user regional formatting consumed by Win95LX applications."""
from dataclasses import dataclass,replace
from datetime import datetime
from decimal import Decimal,ROUND_HALF_UP,localcontext
from functools import lru_cache
from pathlib import Path
import json,re

REGIONS=('English (United States)','English (United Kingdom)','English (Australia)',
         'French (France)','German (Germany)','Spanish (Spain)','Italian (Italy)','Japanese')

@dataclass(frozen=True)
class RegionalPreferences:
    region:str=REGIONS[0]
    decimal:str='.'
    digits:int=2
    grouping:str=','
    group_size:int=3
    negative_sign:str='-'
    negative_format:str='-1.1'
    leading_zero:bool=True
    measurement:str='U.S.'
    list_separator:str=','
    currency:str='$'
    currency_position:str='$1.1'
    currency_negative:str='($1.1)'
    currency_decimal:str='.'
    currency_digits:int=2
    currency_grouping:str=','
    currency_group_size:int=3
    time_style:str='h:mm:ss tt'
    time_separator:str=':'
    am:str='AM'
    pm:str='PM'
    short_date:str='M/d/yy'
    date_separator:str='/'
    long_date:str='dddd, MMMM dd, yyyy'

    def validate(self):
        if self.region not in REGIONS:raise ValueError('Unknown regional setting.')
        for field in ('digits','currency_digits','group_size','currency_group_size'):
            value=getattr(self,field)
            if type(value) is not int or not 0<=value<=9:raise ValueError('Enter a value from 0 through 9.')
        for field in ('decimal','grouping','negative_sign','list_separator','currency','currency_decimal','currency_grouping','time_separator','date_separator','am','pm'):
            value=getattr(self,field)
            if not isinstance(value,str) or len(value)>16 or any(ord(c)<32 for c in value):raise ValueError('Invalid regional symbol.')
        if not self.decimal or not self.currency_decimal or self.decimal==self.grouping or self.currency_decimal==self.currency_grouping:raise ValueError('Decimal and grouping symbols must be different.')
        if type(self.leading_zero) is not bool or self.measurement not in ('U.S.','Metric'):raise ValueError('Invalid number settings.')
        if self.negative_format not in ('(1.1)','-1.1','- 1.1','1.1-','1.1 -'):raise ValueError('Invalid negative number format.')
        if self.currency_position not in ('$1.1','1.1$','$ 1.1','1.1 $'):raise ValueError('Invalid currency position.')
        if self.currency_negative not in ('($1.1)','-$1.1','$-1.1','$1.1-','(1.1$)','-1.1$','1.1-$','1.1$-','-1.1 $','-$ 1.1','1.1 $-','$ 1.1-','$ -1.1','1.1- $','($ 1.1)','(1.1 $)'):raise ValueError('Invalid negative currency format.')
        for field in ('time_style','short_date','long_date'):
            value=getattr(self,field)
            if not isinstance(value,str) or not 1<=len(value)<=80 or any(ord(c)<32 for c in value):raise ValueError('Invalid date or time style.')
        return self

    @classmethod
    def load(cls,path=None):
        try:return cls(**json.loads((path or config_path()).read_text())).validate()
        except (OSError,ValueError,TypeError):return cls()

    def number(self,value,currency=False):
        value=Decimal(str(value));negative=value<0;value=abs(value)
        digits=self.currency_digits if currency else self.digits
        decimal=self.currency_decimal if currency else self.decimal
        grouping=self.currency_grouping if currency else self.grouping
        size=self.currency_group_size if currency else self.group_size
        with localcontext() as context:
            context.prec=max(28,len(value.as_tuple().digits)+abs(value.adjusted())+digits+8)
            text=format(value.quantize(Decimal(1).scaleb(-digits),rounding=ROUND_HALF_UP),f'.{digits}f')
        integer,_,fraction=text.partition('.')
        if size and grouping:
            pieces=[]
            while integer:pieces.insert(0,integer[-size:]);integer=integer[:-size]
            integer=grouping.join(pieces)
        if not self.leading_zero and integer=='0' and digits:integer=''
        body=integer+(decimal+fraction if digits else '')
        if currency:
            pattern=self.currency_negative if negative else self.currency_position
            return re.sub(r'1\.1|\$|-',lambda match:{'1.1':body,'$':self.currency,'-':self.negative_sign}[match[0]],pattern)
        return self.negative_format.replace('1.1',body).replace('-',self.negative_sign) if negative else body

    def date(self,value,style=None):
        style=style or self.short_date
        # Windows date patterns use quoted literal text and case-sensitive M/m.
        names=MONTH_NAMES.get(self.region,MONTH_NAMES[REGIONS[0]])
        weekdays=WEEKDAY_NAMES.get(self.region,WEEKDAY_NAMES[REGIONS[0]])
        tokens={'yyyy':str(value.year),'yy':f'{value.year%100:02}','MMMM':names[value.month-1],
                'MMM':names[value.month-1][:3],'MM':f'{value.month:02}','M':str(value.month),
                'dddd':weekdays[value.weekday()],'ddd':weekdays[value.weekday()][:3],
                'dd':f'{value.day:02}','d':str(value.day),'/':self.date_separator}
        return _pattern(style,tokens)
    def time(self,value,style=None):
        tokens={'HH':f'{value.hour:02}','H':str(value.hour),'hh':f'{value.hour%12 or 12:02}',
                'h':str(value.hour%12 or 12),'mm':f'{value.minute:02}','m':str(value.minute),
                'ss':f'{value.second:02}','s':str(value.second),'tt':self.am if value.hour<12 else self.pm,
                't':(self.am if value.hour<12 else self.pm)[:1],':':self.time_separator}
        return _pattern(style or self.time_style,tokens)
    def calculator_text(self,text):return text.replace('.',self.decimal)
    def calculator_input(self,text):return text.replace(self.grouping,'') .replace(self.decimal,'.') if self.grouping else text.replace(self.decimal,'.')
    def short_time(self,value):return self.time(value,re.sub(r':?ss|ss:?','',self.time_style))
    def list_text(self,values):return self.list_separator.join(str(value) for value in values)

def _pattern(style,tokens):
    matcher=re.compile("'([^']*)'|"+'|'.join(re.escape(key) for key in sorted(tokens,key=len,reverse=True)))
    return matcher.sub(lambda match:match[1] if match[1] is not None else tokens[match[0]],style)

MONTH_NAMES={REGIONS[0]:tuple('January February March April May June July August September October November December'.split()),
 'French (France)':tuple('janvier février mars avril mai juin juillet août septembre octobre novembre décembre'.split()),
 'German (Germany)':tuple('Januar Februar März April Mai Juni Juli August September Oktober November Dezember'.split()),
 'Spanish (Spain)':tuple('enero febrero marzo abril mayo junio julio agosto septiembre octubre noviembre diciembre'.split()),
 'Italian (Italy)':tuple('gennaio febbraio marzo aprile maggio giugno luglio agosto settembre ottobre novembre dicembre'.split()),
 'Japanese':tuple(str(month)+'月' for month in range(1,13))}
WEEKDAY_NAMES={REGIONS[0]:tuple('Monday Tuesday Wednesday Thursday Friday Saturday Sunday'.split()),
 'French (France)':tuple('lundi mardi mercredi jeudi vendredi samedi dimanche'.split()),
 'German (Germany)':tuple('Montag Dienstag Mittwoch Donnerstag Freitag Samstag Sonntag'.split()),
 'Spanish (Spain)':tuple('lunes martes miércoles jueves viernes sábado domingo'.split()),
 'Italian (Italy)':tuple('lunedì martedì mercoledì giovedì venerdì sabato domenica'.split()),
 'Japanese':tuple('月曜日 火曜日 水曜日 木曜日 金曜日 土曜日 日曜日'.split())}

def regional_preset(region):
    p=RegionalPreferences(region=region)
    if region in ('English (United Kingdom)','English (Australia)'):return replace(p,measurement='Metric',currency='£' if 'Kingdom' in region else '$',short_date='dd/MM/yyyy',time_style='HH:mm:ss')
    if region=='Japanese':return replace(p,currency='¥',currency_digits=0,measurement='Metric',short_date='yyyy/MM/dd',time_style='H:mm:ss',long_date="yyyy'年'M'月'd'日'")
    if region in ('French (France)','German (Germany)','Spanish (Spain)','Italian (Italy)'):
        return replace(p,decimal=',',grouping=' ' if region=='French (France)' else '.',currency='€',currency_position='1.1 $',currency_negative='-1.1 $',currency_decimal=',',currency_grouping=' ' if region=='French (France)' else '.',short_date='dd/MM/yyyy',time_style='HH:mm:ss',measurement='Metric')
    return p

def config_path():return Path.home()/'.config/win95lx/regional.json'

@lru_cache(maxsize=16)
def _cached(path,modified,size):return RegionalPreferences.load(path)

def current():
    path=config_path()
    try:state=path.stat()
    except OSError:return RegionalPreferences()
    return _cached(path,state.st_mtime_ns,state.st_size)

class RegionalBackend:
    def __init__(self,path):self.value=RegionalPreferences.load(path)
    def preferences(self):return self.value
    def snapshot(self):return self.value
    def restore(self,value):self.value=value
    def apply(self,value):self.value=value.validate()
