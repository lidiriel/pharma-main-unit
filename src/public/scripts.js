$(function () {
    var $body = $('body');
    var $frames = $('#frames');
    var $hexInput = $('#hex-input');
	var $hexList = $('#hex-list');
    var $insertButton = $('#insert-button');
	var $insertrandButton = $('#insertrand-button');
	var $hexrandButton = $('#hexrand-button');
    var $deleteButton = $('#delete-button');
    var $updateButton = $('#update-button');
	var $deleteallButton = $('#deleteall-button');

    var $leds, $cols, $rows;
	
    function Bitmap(hexString) {
        let matrix = fromHexString(hexString);

        function fromHexString(hexString) {
            const out = [];
            for (let i = 0; i < hexString.length / 2; i++) {
                let byte = parseInt(hexString.substr(i * 2, 2), 16).toString(2);
                byte = ('00000000' + byte).substr(-8);
                out.push(byte.split('').reverse());
            }
            return out.reverse();
        }

        function toHexString() {
            const out = [];
            for (let i = 0; i < matrix.length; i++) {
                let byte = parseInt(matrix[i].slice().reverse().join(''), 2).toString(16);
                byte = ('0' + byte).substr(-2);
                out.push(byte);
            }
            return out.reverse().join('');
        }

        function transpose() {
            for (let i = 0; i < matrix.length; i++) {
                for (let j = i; j < 8; j++) {
                    const tmp = matrix[i][j];
                    matrix[i][j] = matrix[j][i];
                    matrix[j][i] = tmp;
                }
            }
        }

        function shiftLeft() {
            for (let i = 0; i < matrix.length; i++) {
                const len = matrix[i].length - 1;
                for (let j = 0; j < len; j++) {
                    matrix[i][j] = matrix[i][j + 1];
                }
                matrix[i][len] = 0;
            }
        }

        function shiftRight() {
            for (let i = 0; i < matrix.length; i++) {
                const len = matrix[i].length - 1;
                for (let j = len; j > 0; j--) {
                    matrix[i][j] = matrix[i][j - 1];
                }
                matrix[i][0] = 0;
            }
        }

        function rotate() {
            matrix.reverse();
            transpose();
        }

        function rotateBack() {
            transpose();
            matrix.reverse();
        }

        return {
            toHexString: toHexString,
            shiftLeft: shiftLeft,
            shiftRight: shiftRight,
            rotate: rotate,
            rotateBack: rotateBack,
        }
    }

	

    var generator = {
		
		lookup_leds_bits: function(i,j) {
			if(i<0 && i>5){
				console.log("invalid value for i="+i);
			}
			if(j<0 && j>5){
				console.log("invalid value for j="+j);
			}
			const items = [
				[0, 0, 5, 0, 0 ],
			  	[0, 0, 1, 0, 0 ],
			  	[8, 4, 0, 2, 6 ],
			  	[0, 0, 3, 0, 0 ],
			  	[0, 0, 7, 0, 0 ]];
			return Number(items[i][j]);
		},
		lookup_color_leds: function(i,j) {
			const items = [
				['', '', 'g', '', '' ],
			  	['', '', 'b', '', '' ],
			  	['g', 'b', '', 'b', 'g' ],
			  	['', '', 'b', '', '' ],
			  	['', '', 'g', '', '' ]];
			return items[i][j];
		},
        tableLeds: function () {
			var out = [];
			for (var cross = 1; cross < 3; cross++) {
				var addbit = (cross == 1 ? 0 : 8);
				out.push('<div id="leds-cross-'+cross+'"><table id="leds-matrix" class="column">');
	            for (var i = 1; i < 6; i++) {
	                out.push('<tr>');
	                for (var j = 1; j < 6; j++) {
						let bit = generator.lookup_leds_bits(i-1,j-1);
						if(bit == 0){
							out.push('<td class="null" data-row="' + i + '" data-col="' + j + '"></td>');
						}else{
							let color = "green-leds";
							if(generator.lookup_color_leds(i-1,j-1)=='b'){
								color = "blue-leds";
							}
							out.push('<td class="'+color+' item" data-row="' + i + '" data-col="' + j + '" bit="' + bit + '"></td>');
						}
	                }
	                out.push('</tr>');
	            }
				out.push('</table></div>');
			}
            return out.join('');
        }
    };

    var converter = {
        patternToFrame: function (pattern) {
			var out = ['<div class="frame" data-hex="' + pattern + '">'];
			for(var cross = 1; cross < 3; cross++){
				out.push('<table class="column">');
				var byte = pattern.substr((cross-1)*2, 2);
				byte = parseInt(byte, 16);
				for (var i = 1; i < 6; i++) {
	                out.push('<tr>');
	                for (var j = 1; j < 6; j++) {
						let bitnumber = generator.lookup_leds_bits(i-1,j-1);
						if(bitnumber == 0){
							out.push('<td class="null"></td>');
						}else{
							let color = "green-leds";
							if(generator.lookup_color_leds(i-1,j-1)=='b'){
								color = "blue-leds";
							}
							console.log("bitnumber="+bitnumber+" byte="+byte);
		                    if (byte & (1 << (bitnumber-1))) {
		                        out.push('<td class="'+color+' item active"></td>');
		                    } else {
		                        out.push('<td class="item"></td>');
	                    	}
	                	}
					}
	                out.push('</tr>');
	            }
            	out.push('</table>');
			}
			out.push('</div>');
            return out.join('');
        },
        patternsToCodeUint64Array: function (patterns) {
            var out = ['const uint64_t IMAGES[] = {\n'];

            for (var i = 0; i < patterns.length; i++) {
                out.push('  0x');
                out.push(patterns[i]);
                out.push(',\n');
            }
            out.pop();
            out.push('\n};\n');
            out.push('const int IMAGES_LEN = sizeof(IMAGES)/8;\n');

            return out.join('');
        },
        patternsToCodeBytesArray: function (patterns) {
            var out = ['const uint8_t IMAGES[][8] = {\n'];

            for (var i = 0; i < patterns.length; i++) {
                out.push('{\n');
                for (var j = 7; j >= 0; j--) {
                    var byte = patterns[i].substr(2 * j, 2);
                    byte = parseInt(byte, 16).toString(2);
                    byte = ('00000000' + byte).substr(-8);
                    byte = byte.split('').reverse().join('');
                    out.push('  0b');
                    out.push(byte);
                    out.push(',\n');
                }
                out.pop();
                out.push('\n}');
                out.push(',');
            }
            out.pop();
            out.push('};\n');
            out.push('const int IMAGES_LEN = sizeof(IMAGES)/8;\n');
            return out.join('');
        },
        fixPattern: function (pattern) {
            pattern = pattern.replace(/[^0-9a-fA-F]/g, '0');
            return ('0000' + pattern).substr(-4);
        },
        fixPatterns: function (patterns) {
            for (var i = 0; i < patterns.length; i++) {
                patterns[i] = converter.fixPattern(patterns[i]);
            }
            return patterns;
        }
    };

    function makeFrameElement(pattern) {
        pattern = converter.fixPattern(pattern);
		console.log("make frame pattern="+pattern);
        return $(converter.patternToFrame(pattern)).click(onFrameClick);
    }

    function ledsToHex() {
        var out = [];
		for(var c = 1; c <3; c++) {
			let ledscross = $('#leds-cross-'+c);
			let bits = [0, 0, 0, 0, 0, 0, 0, 0,];
	        for (var i = 1; i < 6; i++) {
	            for (var j = 1; j < 6; j++) {
					var element = ledscross.find('.item[data-row=' + i + '][data-col=' + j + '] ');
		            if(element.hasClass('active')){
						var idx = Number(element.attr("bit")) - 1;
						bits[idx] = '1';
					}
	            }
			}
        	bits.reverse();
			bits=bits.join('');
			byte = parseInt(bits, 2).toString(16);
			if(byte.length==1){
				byte="0"+byte;
			}
        	out.push(byte);
		}
        $hexInput.val(out.join(''));
    }

    function hexInputToLeds() {
        var val = getInputHexValue();
		for(var c=1; c<3; c++){
			var byte = val.substr((c-1)*2, 2);
			byte = parseInt(byte, 16);
			let ledscross = $('#leds-cross-'+c);
			for (var i = 1; i < 6; i++) {
	            for (var j = 1; j < 6; j++) {
					var bitnumber = generator.lookup_leds_bits(i-1,j-1);
					if(bitnumber != 0){
						var active = !!(byte & 1 << (bitnumber - 1));	
					}
					ledscross.find('.item[data-row=' + i + '][data-col=' + j + '] ').toggleClass('active', active);
	            }
			}
		}
    }

    var savedHashState;

    function printArduinoCode(patterns) {
        if (patterns.length) {
            var code;
            if ($('#images-as-byte-arrays').prop("checked")) {
                code = converter.patternsToCodeBytesArray(patterns);
            } else {
                code = converter.patternsToCodeUint64Array(patterns);
            }
            $('#output').val(code);
        }
    }

    function framesToPatterns() {
        var out = [];
        $frames.find('.frame').each(function () {
            out.push($(this).attr('data-hex'));
        });
        return out;
    }

    function saveState() {
        var patterns = framesToPatterns();
        window.location.hash = savedHashState = patterns.join('|');
    }

	function loadAllSequences() {
		var posting = $.post("/load", {"sequence_name" : ""});
		posting.done(function(data) {
			for(seq_name in data){
				$("#prog").append(new Option(seq_name, seq_name));
			}
			$("#prog").show();
			var key = $("#prog").val();
			$("#hex-list").val(data[key]);
		});
	}
	
	function loadOneSequence(name) {
		console.log("load sequence name = ", name);
		var posting = $.post("/load", {"sequence_name" : name});
		posting.done(function(data) {
			//$frames.empty();
			$("#hex-list").val(data);
			for (code in data){
				console.log("code is ", code)
				var $newFrame = makeFrameElement(code);
				insert_frame($newFrame);
			}	
		});
		
	}



	
	
//    function loadState() {
//        savedHashState = window.location.hash.slice(1);
//        $frames.empty();
//        var frame;
//        var patterns = savedHashState.split('|');
//        patterns = converter.fixPatterns(patterns);
//
//        for (var i = 0; i < patterns.length; i++) {
//            frame = makeFrameElement(patterns[i]);
//            $frames.append(frame);
//        }
//        frame.addClass('selected');
//        $hexInput.val(frame.attr('data-hex'));
//        //printArduinoCode(patterns);
//        //hexInputToLeds();
//    }

    function getInputHexValue() {
        var hexval = converter.fixPattern($hexInput.val());
    	console.log("hexval="+hexval);
		return hexval;
	}

    function onFrameClick() {
        $hexInput.val($(this).attr('data-hex'));
        processToSave($(this));
        hexInputToLeds();
    }

    function processToSave($focusToFrame) {
        $frames.find('.frame.selected').removeClass('selected');

        if ($focusToFrame.length) {
            $focusToFrame.addClass('selected');
            $deleteButton.removeAttr('disabled');
            $updateButton.removeAttr('disabled');
        } else {
            $deleteButton.attr('disabled', 'disabled');
            $updateButton.attr('disabled', 'disabled');
        }
        saveState();
    }
	
	function insert_frame($newFrame){
		var $selectedFrame = $frames.find('.frame.selected').first();
        if ($selectedFrame.length) {
            $selectedFrame.after($newFrame);
        } else {
            $frames.append($newFrame);
        }
        processToSave($newFrame);
	}

	$('#leds-container').append($(generator.tableLeds()));

    $leds = $('#leds-container');

    $leds.find('.item').mousedown(function () {
        $(this).toggleClass('active');
        ledsToHex();
    });


    $hexInput.keyup(function () {
        hexInputToLeds();
    });

    $deleteButton.click(function () {
        var $selectedFrame = $frames.find('.frame.selected').first();
        var $nextFrame = $selectedFrame.next('.frame').first();

        if (!$nextFrame.length) {
            $nextFrame = $selectedFrame.prev('.frame').first();
        }

        $selectedFrame.remove();

        if ($nextFrame.length) {
            $hexInput.val($nextFrame.attr('data-hex'));
        }

        processToSave($nextFrame);

        hexInputToLeds();
    });

    $insertButton.click(function () {
        var $newFrame = makeFrameElement(getInputHexValue());
		insert_frame($newFrame);
    });

    $updateButton.click(function () {
        var $newFrame = makeFrameElement(getInputHexValue());
        var $selectedFrame = $frames.find('.frame.selected').first();

        if ($selectedFrame.length) {
            $selectedFrame.replaceWith($newFrame);
        } else {
            $frames.append($newFrame);
        }

        processToSave($newFrame);
    });
	
	$deleteallButton.click(function () {
		$frames.empty();
	});

    $('#output').on('paste', function (e) {
        var value = e.originalEvent.clipboardData.getData('text');

        const hash = parseArduinoCode(value);
        if (hash) {
            location.hash = hash;
        } else {
            alert("Couldn't parse pasted code as valid LED Matrix Editor-generated C ;(");
        }
    });

    $('#output').focus(function() {
        $(this).select();
    });

    
	$( function() {
		$("#prog").selectmenu();
		
		$("#prog").change( function (e) {
			var optionSelected = $("#prog").val();
			loadOneSequence(optionSelected);
		});
		
		
	} );

    $frames.sortable({
        stop: function (event, ui) {
            saveState();
        }
    });

	loadAllSequences();

});
