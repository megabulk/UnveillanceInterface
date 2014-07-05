var UV;

function randomString() {
	return Math.random().toString(36).replace(/[^a-z]+/g, '');
}

function getFileContent(ctx, path, callback) {
	$.ajax({
		url: "/files/" + path,
		method: "get",
		complete: callback,
		context: ctx
	});
}

function setRawAsset(el, path) {
	$(el).empty();
	getFileContent(this, path, function(res) {
		console.info(res);
		$(el).append($(document.createElement('textarea')).html(res.responseText));
	});
}

function JSONtoURLString(json) {
	var url_str = Object.keys(json).map(function(key) {
		return (encodeURIComponent(key) + "=" + encodeURIComponent(json[key]));
	}).join('&');
	return url_str;
}

function toggleElement(el) {
	if($(el).css('display') == "block") {
		$(el).css('display','none');
		return false;
	} else {
		$(el).css('display','block');
		return true;
	}
}

function showErrorMessage(el, msg) {
	$(el).html(msg);
	$(el).css('visibility','visible');
}

function validateFormField(field, form_root) {	
	var val = $(field).val();
	
	if($(field).hasClass('uv_mandatory_dz')) {
		val = $(field).html();
	}
	var name = $(field).attr('name');
				
	if($(field).hasClass('uv_mandatory') || $(field).hasClass('uv_mandatory_dz')) {
		if(val == "") {
			$(field).addClass("uv_invalid");
			showErrorMessage($(field).siblings(".uv_error_msg")[0], "Required.");
			return false;
		}
	}
	
	if($(field).hasClass('uv_confirm')) {
		var check_name = name.replace(".confirm", "");
		var check_input = $(form_root).find("input[name='" + check_name + "']")[0];
		
		if(val != $(check_input).val()) {
			$(field).addClass("uv_invalid");
			showErrorMessage(
				$(field).siblings(".uv_error_msg")[0], 
				$(field).attr('uv_error_msg'));
			
			return false;
		}		
	}
	
	return true;
}

function doInnerAjax(url, method, data, callback, async) {
	console.info(async);
	if(async === undefined) { async = true; }
	console.info(async);
	var a = $.ajax({
		url: "/" + url + "/",
		dataType: "json",
		data: data,
		method: method,
		complete: callback,
		async: async
	});
	
	if(!async) {
		console.info(a.success());
		return a.success();
	}
}

function getTemplate(tmpl, on_complete, static_root, ctx) {
	if(!static_root) { static_root = "/web/layout/tmpl/"; }
	
	var a_obj = {
		url : (static_root + tmpl),
		method: "get",
		dataType: "html",
		context: ctx
	};
	
	if(on_complete) { a_obj.complete = on_complete; }
	
	$.ajax(a_obj);
}

function translate(obj) {
	new_html = $(obj).html();
	
	if($(obj).hasClass("uv_date")) {
		new_html = moment(Number(new_html)).format("MM-DD-YYYY HH:mm");
	}
	
	if($(obj).hasClass("uv_none_if_null")) {
		if(new_html.length == 0) {
			new_html = "none";
		}
	}
	
	if($(obj).hasClass("uv_unknown_if_null")) {
		if(new_html.length == 0) {
			new_html = "unknown";
		}
	}
	
	if($(obj).hasClass("uv_false_if_null")) {
		if(new_html.length == 0) {
			new_html = "false";
		}
	}
	
	if($(obj).attr('repl')) {
		console.info("OMG " + $(obj).attr('repl'));
		new_html = $(obj).attr('repl') + new_html;
	}
	
	return new_html;
}

function insertTemplate(tmpl, data, append_root, on_complete, static_root) {
	if(data == null) { data = {}; }
	if(!static_root) { static_root = "/web/layout/tmpl/"; }
	
	var a_obj = {
		url : (static_root + tmpl),
		method: "get",
		dataType: "html",
		success: function(html) {
			$(append_root).html(Mustache.to_html(html, data));
			$.each($(append_root).find(".uv_translate"), function(idx, item) {
				if(item.tagName.toLowerCase() == "img" && $(item).attr('repl')) {
					$(item).prop('src', $(item).prop('src').replace($(item).attr('repl'), translate(item)));
				} else {
					$(item).html(translate(item));
				}
			});
		}
	};
	
	if(on_complete) { a_obj.complete = on_complete; }
	
	$.ajax(a_obj);
}

function removeEl() {
	console.info("removing a genereric element");
	console.info(this);
}

function doPost(endpoint, in_el, out_el) {
	if(in_el[0] != "#") {
		in_el = "#" + in_el;
	}
	
	if(out_el[0] != "#") {
		out_el = "#" + out_el;
	}
	
	console.info(endpoint);
	
	data = {}
	
	switch($(in_el).get(0).tagName.toLowerCase()) {
		case "textarea":
			data['input'] = $(in_el).val();
			break;
	}
	
	doInnerAjax(endpoint, "post", data, function(json) {
		console.info(json);
		console.info($(out_el));
		$(out_el).html(JSON.stringify(json));
	});
}