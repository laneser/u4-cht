/* 用 xu4 的 U4 LZW 解碼器解 Amiga .LWZ。試不同 header offset。
   用法:lzw_unpack <in.LWZ> <out.bin> [skip_bytes] */
#include <stdio.h>
#include <stdlib.h>
#include "lzw/u4decode.h"
int main(int argc, char**argv){
    if(argc<3){fprintf(stderr,"usage: %s in out [skip]\n",argv[0]);return 1;}
    int skip = argc>3?atoi(argv[3]):0;
    FILE*f=fopen(argv[1],"rb"); fseek(f,0,SEEK_END); long n=ftell(f); fseek(f,0,SEEK_SET);
    unsigned char*buf=malloc(n); fread(buf,1,n,f); fclose(f);
    void*out=NULL;
    long outlen=decompress_u4_memory(buf+skip, n-skip, &out);
    fprintf(stderr,"in=%ld skip=%d -> out=%ld\n", n, skip, outlen);
    if(outlen>0){ FILE*o=fopen(argv[2],"wb"); fwrite(out,1,outlen,o); fclose(o); }
    return outlen>0?0:2;
}
