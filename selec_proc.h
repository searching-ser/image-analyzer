#ifndef SELEC_PROC_H
#define SELEC_PROC_H

extern void inv_img(char mask[], char path[]);
extern void inv_img_grey(char mask[], char path[]);
extern void inv_img_color(char mask[], char path[]);
extern void inv_img_grey_horizontal(char mask[], char path[]);
extern void inv_img_grey_vertical(char mask[], char path[]);
extern void inv_img_color_horizontal(char mask[], char path[]);
extern void inv_img_color_vertical(char mask[], char path[]);
extern void desenfoque(char path[], char mask[], int kernel);
extern void desenfoque_grey(char path[], char mask[], int kernel);
extern void desenfoque_color(char path[], char mask[], int kernel);

#endif
