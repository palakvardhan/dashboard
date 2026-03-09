import urllib.request, json

MB_KEY = 'mb_1dsbxsJfyROPsVyNpifJ8hTTlIDG85+qNKRo91KDnb4='
BASE = 'https://metabase.wiom.in/api'

sqls = {}

# Revert Total Tickets: put back SUB_STATUS NOT IN filter
# L2 Count & L2 Res% stay on correct definition
sqls[10438] = """
WITH ist AS (SELECT CONVERT_TIMEZONE('UTC','Asia/Kolkata',CURRENT_TIMESTAMP())::DATE AS today),
kapture AS (
  SELECT TRY_TO_DATE(CREATED_DATE,'DD/MM/YYYY') AS cdate,
    TICKET_NO, STATUS, SUB_STATUS,
    (TRY_TO_NUMBER(SPLIT_PART(DIFF_TIME_CREATE_AND_RESOLVE_WORKING_HOURS,':',1))*60
     + TRY_TO_NUMBER(SPLIT_PART(DIFF_TIME_CREATE_AND_RESOLVE_WORKING_HOURS,':',2))
     + TRY_TO_NUMBER(SPLIT_PART(DIFF_TIME_CREATE_AND_RESOLVE_WORKING_HOURS,':',3))/60.0) AS tat_mins
  FROM KAPTURE_PARTNER_TICKETS_REPORT, ist
  WHERE TRY_TO_DATE(CREATED_DATE,'DD/MM/YYYY') >= DATE_TRUNC('month', ist.today)
    AND TICKET_TYPE_PARENT_SUB = 'Parent Ticket'
    AND SUB_STATUS NOT IN ('Customer Replied','Unattended','Replied')
  QUALIFY ROW_NUMBER() OVER (PARTITION BY TICKET_NO ORDER BY CONVERT_TIMEZONE('UTC','Asia/Kolkata',INGESTED_AT) DESC NULLS LAST) = 1
),
periods AS (
  SELECT 'D-1' AS period, 1 AS s, DATEADD(day,-1,ist.today) p0, DATEADD(day,-1,ist.today) p1 FROM ist
  UNION ALL SELECT 'D-2',2,DATEADD(day,-2,ist.today),DATEADD(day,-2,ist.today) FROM ist
  UNION ALL SELECT 'D-3',3,DATEADD(day,-3,ist.today),DATEADD(day,-3,ist.today) FROM ist
  UNION ALL SELECT 'MTD',4,DATE_TRUNC('month',ist.today),DATEADD(day,-1,ist.today) FROM ist
)
SELECT
  p.period AS "Period",
  SUM(CASE WHEN k.SUB_STATUS IN ('Completed','Open','Resolved') THEN 1 ELSE 0 END) AS "L2 Count",
  ROUND(100.0*SUM(CASE WHEN k.STATUS='Complete' AND k.SUB_STATUS IN ('Completed','Open','Resolved') THEN 1 ELSE 0 END)
    /NULLIF(SUM(CASE WHEN k.SUB_STATUS IN ('Completed','Open','Resolved') THEN 1 ELSE 0 END),0),1) AS "L2 Res%",
  ROUND(MEDIAN(CASE WHEN k.STATUS='Complete' AND k.SUB_STATUS IN ('Completed','Open','Resolved') AND k.tat_mins>0 THEN k.tat_mins END),0) AS "L2 Med TAT (mins)",
  SUM(CASE WHEN k.STATUS='Complete' AND k.SUB_STATUS IN ('Completed','Open','Resolved') AND k.tat_mins<=1440 THEN 1 ELSE 0 END) AS "L2 Resolved <=24h",
  SUM(CASE WHEN k.STATUS='Complete' AND k.SUB_STATUS IN ('Completed','Open','Resolved') AND k.tat_mins<=2880 THEN 1 ELSE 0 END) AS "L2 Resolved <=48h",
  COUNT(k.TICKET_NO) AS "Total Tickets",
  ROUND(100.0*SUM(CASE WHEN k.SUB_STATUS='Resolved on Call' THEN 1 ELSE 0 END)/NULLIF(COUNT(k.TICKET_NO),0),1) AS "Resolved% (On-Call)"
FROM periods p LEFT JOIN kapture k ON k.cdate BETWEEN p.p0 AND p.p1
GROUP BY p.period,p.s ORDER BY p.s
"""

# Updated card 10446: add L2 Res% <=24h as second column
sqls[10446] = """
WITH ist AS (SELECT CONVERT_TIMEZONE('UTC','Asia/Kolkata',CURRENT_TIMESTAMP())::DATE AS today),
dedup AS (
  SELECT TICKET_NO, TRY_TO_DATE(CREATED_DATE,'DD/MM/YYYY') AS cdate,
    STATUS, SUB_STATUS,
    (TRY_TO_NUMBER(SPLIT_PART(DIFF_TIME_CREATE_AND_RESOLVE_WORKING_HOURS,':',1))*60
     + TRY_TO_NUMBER(SPLIT_PART(DIFF_TIME_CREATE_AND_RESOLVE_WORKING_HOURS,':',2))
     + TRY_TO_NUMBER(SPLIT_PART(DIFF_TIME_CREATE_AND_RESOLVE_WORKING_HOURS,':',3))/60.0) AS tat_mins
  FROM KAPTURE_PARTNER_TICKETS_REPORT, ist
  WHERE TRY_TO_DATE(CREATED_DATE,'DD/MM/YYYY') >= DATEADD(day,-7, ist.today)
    AND TRY_TO_DATE(CREATED_DATE,'DD/MM/YYYY') < ist.today
    AND TICKET_TYPE_PARENT_SUB = 'Parent Ticket'
    AND SUB_STATUS NOT IN ('Customer Replied','Unattended','Replied')
  QUALIFY ROW_NUMBER() OVER (PARTITION BY TICKET_NO ORDER BY CONVERT_TIMEZONE('UTC','Asia/Kolkata',INGESTED_AT) DESC NULLS LAST) = 1
)
SELECT
  cdate AS "Date",
  ROUND(100.0*SUM(CASE WHEN STATUS='Complete' AND SUB_STATUS IN ('Completed','Open','Resolved') THEN 1 ELSE 0 END)
    /NULLIF(SUM(CASE WHEN SUB_STATUS IN ('Completed','Open','Resolved') THEN 1 ELSE 0 END),0),1) AS "L2 Res%",
  ROUND(100.0*SUM(CASE WHEN STATUS='Complete' AND SUB_STATUS IN ('Completed','Open','Resolved') AND tat_mins<=1440 THEN 1 ELSE 0 END)
    /NULLIF(SUM(CASE WHEN SUB_STATUS IN ('Completed','Open','Resolved') THEN 1 ELSE 0 END),0),1) AS "L2 Res% <=24h"
FROM dedup
GROUP BY 1 ORDER BY 1
"""

sqls[10439] = """
WITH ist AS (SELECT CONVERT_TIMEZONE('UTC','Asia/Kolkata',CURRENT_TIMESTAMP()) AS ts,
                    CONVERT_TIMEZONE('UTC','Asia/Kolkata',CURRENT_TIMESTAMP())::DATE AS today),
sla_monthly AS (
  SELECT CAST(DATE_TRUNC('MONTH',CONVERT_TIMEZONE('UTC','Asia/Kolkata',TASK_RESOLVED_TIME)) AS DATE) AS MONTH,
    PARTNER_ACCOUNTID, PERFORMANCE_METRIC,
    COALESCE(SUM(SCORE)/COUNT(ENTRY_EPOCH_TIME),0) AS sla
  FROM PROD_DB.DYNAMODB.TASK_PERFORMANCE, ist
  WHERE CAST(DATE_TRUNC('MONTH',CONVERT_TIMEZONE('UTC','Asia/Kolkata',TASK_RESOLVED_TIME)) AS DATE) > DATEADD('MONTH',-6, ist.ts)
  GROUP BY 1,2,3
),
sla_agg AS (
  SELECT PARTNER_ACCOUNTID,
    COALESCE(AVG(CASE WHEN PERFORMANCE_METRIC='STRIKE_RATE'
      AND MONTH >= DATE_TRUNC('month', DATEADD('month',-3, ist.ts))
      AND MONTH < DATE_TRUNC('month', ist.ts) THEN sla END),-1) AS sla_avg
  FROM sla_monthly, ist GROUP BY 1
),
app_eng AS (
  SELECT PARTNER_ACCOUNT_ID,
    COUNT(DISTINCT DATE_TRUNC('minute',CONVERT_TIMEZONE('UTC','Asia/Kolkata',TO_TIMESTAMP(timestamp)))) AS app_opens
  FROM PROD_DB.PUBLIC.CT_PARTNER_APP_LAUNCH, ist
  WHERE CONVERT_TIMEZONE('UTC','Asia/Kolkata',TO_TIMESTAMP(timestamp))::DATE >= DATEADD(day,-30, ist.today)
    AND PARTNER_ACCOUNT_ID IS NOT NULL AND PARTNER_ACCOUNT_ID != ''
    AND USER_ROLE IN ('OWNER','ADMIN')
  GROUP BY 1
),
partner_bucket AS (
  SELECT sm.PARTNER_ACCOUNT_ID, sm.PARTNER_NAME, sm.PARTNER_MOBILE,
    CASE WHEN COALESCE(s.sla_avg,-1) < 0.8 OR COALESCE(s.sla_avg,-1) < 0 THEN 'L' ELSE 'H' END
      || CASE WHEN COALESCE(ae.app_opens,0) > 0 THEN 'H' ELSE 'L' END AS final_bucket
  FROM SUPPLY_MODEL sm
  LEFT JOIN sla_agg s  ON s.PARTNER_ACCOUNTID   = sm.PARTNER_ACCOUNT_ID
  LEFT JOIN app_eng ae ON ae.PARTNER_ACCOUNT_ID = sm.PARTNER_ACCOUNT_ID
),
kapture AS (
  SELECT k.TICKET_NO, k.CUSTOMER_CODE, k.STATUS, k.SUB_STATUS,
    (TRY_TO_NUMBER(SPLIT_PART(k.DIFF_TIME_CREATE_AND_RESOLVE_WORKING_HOURS,':',1))*60
     + TRY_TO_NUMBER(SPLIT_PART(k.DIFF_TIME_CREATE_AND_RESOLVE_WORKING_HOURS,':',2))
     + TRY_TO_NUMBER(SPLIT_PART(k.DIFF_TIME_CREATE_AND_RESOLVE_WORKING_HOURS,':',3))/60.0) AS tat_mins
  FROM KAPTURE_PARTNER_TICKETS_REPORT k, ist
  WHERE TRY_TO_DATE(k.CREATED_DATE,'DD/MM/YYYY') = DATEADD(day,-1, ist.today)
    AND k.TICKET_TYPE_PARENT_SUB = 'Parent Ticket'
    AND k.SUB_STATUS NOT IN ('Customer Replied','Unattended','Replied')
  QUALIFY ROW_NUMBER() OVER (PARTITION BY k.TICKET_NO ORDER BY CONVERT_TIMEZONE('UTC','Asia/Kolkata',k.INGESTED_AT) DESC NULLS LAST) = 1
)
SELECT
  COALESCE(pb.final_bucket,'Unknown') AS "Partner Category",
  SUM(CASE WHEN k.SUB_STATUS IN ('Completed','Open','Resolved') THEN 1 ELSE 0 END) AS "L2 Count",
  ROUND(100.0*SUM(CASE WHEN k.STATUS='Complete' AND k.SUB_STATUS IN ('Completed','Open','Resolved') THEN 1 ELSE 0 END)
    /NULLIF(SUM(CASE WHEN k.SUB_STATUS IN ('Completed','Open','Resolved') THEN 1 ELSE 0 END),0),1) AS "L2 Res%",
  ROUND(MEDIAN(CASE WHEN k.STATUS='Complete' AND k.SUB_STATUS IN ('Completed','Open','Resolved') AND k.tat_mins>0 THEN k.tat_mins END),0) AS "L2 Med TAT (mins)",
  SUM(CASE WHEN k.STATUS='Complete' AND k.SUB_STATUS IN ('Completed','Open','Resolved') AND k.tat_mins<=1440 THEN 1 ELSE 0 END) AS "L2 Resolved <=24h",
  SUM(CASE WHEN k.STATUS='Complete' AND k.SUB_STATUS IN ('Completed','Open','Resolved') AND k.tat_mins<=2880 THEN 1 ELSE 0 END) AS "L2 Resolved <=48h",
  COUNT(k.TICKET_NO) AS "Total Tickets",
  ROUND(100.0*SUM(CASE WHEN k.SUB_STATUS='Resolved on Call' THEN 1 ELSE 0 END)/NULLIF(COUNT(k.TICKET_NO),0),1) AS "Resolved% (On-Call)"
FROM partner_bucket pb
JOIN kapture k ON k.CUSTOMER_CODE = pb.PARTNER_ACCOUNT_ID
GROUP BY 1 ORDER BY "L2 Count" DESC
"""

def get_card(card_id):
    req = urllib.request.Request(f'{BASE}/card/{card_id}')
    req.add_header('x-api-key', MB_KEY)
    with urllib.request.urlopen(req) as r:
        return json.loads(r.read())

def update_card(card_id, sql):
    card = get_card(card_id)
    card['dataset_query']['native']['query'] = sql.strip()
    payload = json.dumps({'dataset_query': card['dataset_query']}).encode()
    req = urllib.request.Request(f'{BASE}/card/{card_id}', data=payload, method='PUT')
    req.add_header('Content-Type', 'application/json')
    req.add_header('x-api-key', MB_KEY)
    with urllib.request.urlopen(req) as r:
        return json.loads(r.read()).get('name', '?')

for card_id, sql in sqls.items():
    try:
        name = update_card(card_id, sql)
        print(f'OK  Card {card_id}: {name}')
    except Exception as e:
        print(f'ERR Card {card_id}: {e}')
