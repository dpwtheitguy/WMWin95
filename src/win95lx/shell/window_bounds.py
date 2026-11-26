"""Keep native-size property sheets and resizable windows in the work area."""
def fit_bounds(bounds,screen,*,resizable=False,taskbar=28):
    x,y,width,height=bounds;screen_width,screen_height=screen
    available=max(1,screen_height-taskbar)
    if resizable:width=min(width,screen_width);height=min(height,available)
    return (max(0,min(x,max(0,screen_width-width))),max(0,min(y,max(0,available-height))),width,height)
