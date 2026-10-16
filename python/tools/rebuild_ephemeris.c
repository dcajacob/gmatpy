/* GMAT Py maintainers, independent GMAT Py project, 2026-10-01.
 * Re-create selected SPK segments from authoritative NAIF originals using
 * CSPICE SPKSUB; no astronomical samples are interpolated or refitted here.
 * Apache-2.0 applies to this new utility, not to the NAIF input kernels.
 */
#include "SpiceUsr.h"
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

typedef struct {SpiceInt target, center, frame, type; SpiceDouble begin,end;} Segment;
static int check(void) {
  if (!failed_c()) return 0;
  SpiceChar msg[1841];getmsg_c("LONG",1841,msg);fprintf(stderr,"%s\n",msg);return 1;
}
int main(int argc,char **argv) {
  if(argc!=4) {fprintf(stderr,"usage: rebuild_spk sources-dir output comments\n");return 2;}
  erract_c("SET",0,"RETURN");errprt_c("SET",0,"NONE");
  SpiceInt h,iv[6],out; SpiceDouble sum[125],dv[2]; SpiceBoolean found;
  /* Preserve the published GMAT DE405AllPlanets selection and its actual
   * per-body coverage, including the shorter satellite-ephemeris ranges.
   * ET is seconds TDB past J2000. These are selection descriptors; all
   * astronomical coefficient payloads are copied from authoritative inputs.
   */
  const Segment segs[] = {
    {499,4,1,2,-315576000,1577880000}, {299,2,1,2,-315576000,1577880000},
    {199,1,1,2,-315576000,1577880000}, {399,3,1,2,-315576000,1577880000},
    {301,3,1,2,-315576000,1577880000}, {10,0,1,2,-315576000,1577880000},
    {9,0,1,2,-315576000,1577880000}, {8,0,1,2,-315576000,1577880000},
    {7,0,1,2,-315576000,1577880000}, {6,0,1,2,-315576000,1577880000},
    {5,0,1,2,-315576000,1577880000}, {4,0,1,2,-315576000,1577880000},
    {3,0,1,2,-315576000,1577880000}, {2,0,1,2,-315576000,1577880000},
    {1,0,1,2,-315576000,1577880000}, {599,5,1,3,-315576000,1577880000},
    {699,6,1,3,-315576000,788961600}, {799,7,1,3,-157723200,788961600},
    {899,8,1,3,-43135.816087188054,1546084865.1838341},
    {999,9,1,3,-43200,1577880000}
  };
  int count=sizeof(segs)/sizeof(segs[0]); SpiceChar id[81];
  spkopn_c(argv[2],"GMAT Py DE405 selected-body merge 2026-10-01",20000,&out);
  if(check())return 1;
  for(int i=0;i<count;i++) {
    Segment s=segs[i]; const char *file="de405.bsp";
    if(s.target==599)file="jup230l.bsp";
    if(s.target==699)file="sat132.bsp";
    if(s.target==799)file="ura063.bsp";
    if(s.target==899)file="nep057.bsp";
    if(s.target==999)file="plu006-5.bsp";
    char path[2048];if(snprintf(path,sizeof(path),"%s/%s",argv[1],file)>=(int)sizeof(path))return 2;
    dafopr_c(path,&h);dafbfs_c(h);daffna_c(&found);int copied=0;
    while(found) {
      dafgs_c(sum);dafus_c(sum,2,6,dv,iv);dafgn_c(81,id);
      if(iv[0]==s.target && iv[1]==s.center && iv[2]==s.frame && iv[3]==s.type
         && dv[0]<=s.begin && dv[1]>=s.end) {
        spksub_c(h,sum,id,s.begin,s.end,out);copied++;break;
      }
      daffna_c(&found);
    }
    dafcls_c(h);if(check())return 1;
    if(copied!=1) {fprintf(stderr,"No unique covering source for body %d\n",s.target);return 1;}
  }
  FILE *comments=fopen(argv[3],"r");if(!comments)return 2;
  char line[255];while(fgets(line,sizeof(line),comments)) {
    size_t n=strlen(line);if(n && line[n-1]=='\n')line[n-1]=0;
    dafac_c(out,1,sizeof(line),line);
  }
  fclose(comments);spkcls_c(out);if(check())return 1;return 0;
}
