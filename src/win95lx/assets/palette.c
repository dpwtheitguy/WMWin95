/* Exact equivalent of display_preferences.py's palette rules. No X11/GTK API. */
#include <stdint.h>
#include <stddef.h>
#include <string.h>

static const uint32_t vga[16]={0x000000,0x800000,0x008000,0x808000,
    0x000080,0x800080,0x008080,0xc0c0c0,0x808080,0xff0000,
    0x00ff00,0xffff00,0x0000ff,0xff00ff,0x00ffff,0xffffff};

int win95lx_palette_abi(void){return 1;}
static unsigned slot(uint32_t key,unsigned mask){return (key*2654435761u)&mask;}

int win95lx_palette_over_256(const uint32_t *pixels,size_t count){
    uint32_t keys[1024];unsigned char used[1024]={0};unsigned colors=0;
    uint32_t previous=0;int have_previous=0;
    if(!pixels)return -1;
    for(size_t i=0;i<count;i++){
        uint32_t key=pixels[i];
        if(have_previous&&key==previous)continue;
        have_previous=1;previous=key;
        unsigned index=slot(key,1023);
        while(used[index]&&keys[index]!=key)index=(index+1)&1023;
        if(!used[index]){
            used[index]=1;keys[index]=key;
            if(++colors>256)return 1;
        }
    }
    return 0;
}

static unsigned distance(unsigned r,unsigned g,unsigned b,uint32_t candidate){
    int dr=(int)r-(int)((candidate>>16)&255),dg=(int)g-(int)((candidate>>8)&255),db=(int)b-(int)(candidate&255);
    return (unsigned)(dr*dr+dg*dg+db*db);
}

static uint32_t convert(uint32_t value,int palette){
    unsigned r,g,b;
    if(palette==0){r=((value>>20)&15)*17;g=((value>>12)&15)*17;b=((value>>4)&15)*17;}
    else{
        r=(value>>16)&255;g=(value>>8)&255;b=value&255;
        for(unsigned i=0;i<16;i++)if((value&0xffffff)==vga[i])return vga[i];
    }
    uint32_t result=vga[0];unsigned best=distance(r,g,b,result);
    for(unsigned i=1;i<16;i++){
        unsigned candidate=distance(r,g,b,vga[i]);
        if(candidate<best){best=candidate;result=vga[i];}
    }
    if(palette==1){
        uint32_t cube=(((r+25)/51*51)<<16)|(((g+25)/51*51)<<8)|((b+25)/51*51);
        unsigned score=distance(r,g,b,cube);
        if(score<best){best=score;result=cube;}
        unsigned gray=((r+g+b)*46+765)/1530*255/23;
        uint32_t candidate=(gray<<16)|(gray<<8)|gray;
        if(distance(r,g,b,candidate)<best)result=candidate;
    }
    return result;
}

int win95lx_palette_convert(const uint32_t *input,uint32_t *output,size_t count,int palette){
    uint32_t keys[4096],values[4096];unsigned char used[4096]={0};
    if(!input||!output||(palette!=0&&palette!=1))return -1;
    uint32_t previous=0,previous_result=0;int have_previous=0;
    for(size_t i=0;i<count;i++){
        uint32_t key=input[i],result;
        if(have_previous&&key==previous){output[i]=previous_result;continue;}
        unsigned index=slot(key,4095),attempt=0;
        while(used[index]&&keys[index]!=key&&attempt<16){index=(index+1)&4095;attempt++;}
        if(used[index]&&keys[index]==key)result=values[index];
        else{
            result=convert(key,palette);
            if(!used[index]){used[index]=1;keys[index]=key;values[index]=result;}
        }
        output[i]=result;previous=key;previous_result=result;have_previous=1;
    }
    return 0;
}
