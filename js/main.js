function main() {
	clock();
	health();
	trains();
}

function health() {
	//todo
	var dateModified = new Date(document.lastModified)
	var now = new Date();
	var diff = (now - dateModified)/(60000) //in minutes
	//console.log(diff)
	if (diff > 60) { //if html file not updated in last hour, warn that something is up
		document.getElementById('outofdate').innerHTML = "Warning - data is " + Math.round(diff/60) + " hours old"
	}
	setTimeout(health, 1000 * 10 * 1); //check every 1 minutes

}

function clock() {
  var today = new Date();
  var h = today.getHours();
  var m = today.getMinutes();
  var s = today.getSeconds();
  h = checkTime(h);
  m = checkTime(m);
  s = checkTime(s);
  document.getElementById('jsclock').innerHTML =
  h + ":" + m; //  + ":" + s;
  var t = setTimeout(clock, 500);
}
function checkTime(i) {
  if (i < 10) {i = "0" + i};  // add zero in front of numbers < 10
  return i;
}

function trains() {
	try {
		var request = new XMLHttpRequest()
		request.open('GET', 'http://192.168.1.3/cgi-bin/traindelays.py', true)
		request.onload = function() {
			var delays = this.response;
			if (delays == 0) {
				out = "Tågen verkar vara i tid."
			} else {
				out = "Tågen är sena!"
				document.getElementById('trainStatus').style.color = "#DD1000";
			}
			document.getElementById('trainStatus').innerHTML = out;
		}
		request.send();
	} catch (e) {
		console.log(e);
	}
	setTimeout(trains, 1000 * 10 * 5); //check every 5 minutes
}

