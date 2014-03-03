$(document).ready(function () { 
	var subpage;
	      if ((subpage = window.location.hash.substring(1)) == "") {
	          window.location = "#";
	          subpage = "1";  
	      }
	    
	            $("#" + subpage+ "-page").fadeIn(600, function() {
	              window.scrollTo(0, 0);  
	          }); 


	      // Page Transitions 
	      $('.breadcrumb > li').click(function() {
	          target = $(this).children('a').attr("href") + "-page";
	           
	          if(target != window.location.hash.substring(1)){

	           $('#everything > div:not(:hidden)').fadeOut(300, function() {
	              window.scrollTo(0,0);
	              $(target).fadeIn(400);

	              });
	          }
	          

	         
	      });

})