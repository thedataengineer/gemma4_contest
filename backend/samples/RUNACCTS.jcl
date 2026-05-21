//RUNACCTS JOB (FIN-001),'NIGHTLY ACCOUNT UPDATE',
//             CLASS=A,MSGCLASS=X,REGION=0M
//*
//*  Nightly batch:
//*    1. Open the production customer MASTER file (read-only).
//*    2. Apply fees and amortization via ACC-UPDATE (which in turn
//*       internally CALLs MORTGAGE-CALC for the interest math).
//*    3. Stream every mutation into a freshly catalogued AUDIT.LOG.
//*
//STEP010  EXEC PGM=ACC-UPDATE
//MASTER   DD DSN=PROD.FIN.MASTER.DAT,DISP=SHR
//AUDIT    DD DSN=PROD.FIN.AUDIT.LOG,
//             DISP=(NEW,CATLG,DELETE),
//             SPACE=(CYL,(50,10),RLSE),
//             DCB=(RECFM=FB,LRECL=100,BLKSIZE=27800)
//SYSOUT   DD SYSOUT=*
//SYSPRINT DD SYSOUT=*
