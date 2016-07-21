$.fn.hScroll = function( options )
 {
   function scroll( obj, e )
   {
     var evt = e.originalEvent;
     var direction = evt.detail ? evt.detail * (-120) : evt.wheelDelta;

     if( direction > 0)
     {
        direction =  $(obj).scrollLeft() - 120;
     }
     else
     {
        direction = $(obj).scrollLeft() + 120;
     }

     $(obj).scrollLeft( direction );

     e.preventDefault();
   }

   $(this).width( $(this).find('div').width() );

   $(this).bind('DOMMouseScroll mousewheel', function( e )
   {
    scroll( this, e );
   });
}