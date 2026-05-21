//NIGHTLY  JOB (BATCH-NTE),'END-OF-DAY MASTER BATCH',
//             CLASS=A,MSGCLASS=X,REGION=0M,
//             NOTIFY=&SYSUID
//*
//*  Master end-of-day orchestration.
//*  STEP010  Refresh DB2 customer + metrics tables via DB-INTERFACE.
//*  STEP020  Account update + amortization pass (conditional on STEP010
//*           returning RC=0, i.e. DB connect succeeded).
//*  STEP030  Tail of the master AUDIT.LOG written to SYSOUT for the
//*           overnight ops monitor.
//*
//STEP010  EXEC PGM=DB-INTERFACE
//ERRLOG   DD DSN=PROD.DB.ERR.LOG,DISP=MOD
//SYSOUT   DD SYSOUT=*
//*
//STEP020  EXEC PGM=ACC-UPDATE,COND=(0,LT,STEP010)
//MASTER   DD DSN=PROD.FIN.MASTER.DAT,DISP=SHR
//AUDIT    DD DSN=PROD.FIN.AUDIT.LOG,
//             DISP=(NEW,CATLG,DELETE),
//             SPACE=(CYL,(50,10),RLSE)
//SYSOUT   DD SYSOUT=*
//*
//STEP030  EXEC PGM=IEBGENER,COND=(0,LT,STEP020)
//SYSUT1   DD DSN=PROD.FIN.AUDIT.LOG,DISP=SHR
//SYSUT2   DD SYSOUT=*
//SYSIN    DD DUMMY
//SYSPRINT DD SYSOUT=*
