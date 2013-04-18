let
	var x: Integer;
    var y: Integer;
    var z: Integer;
    func foo(x: Integer, y:Integer): Integer
    	begin
        	x := x + 1;
            return x + y;
        end
in
	begin
        x := 3;
    	y := 4;
     	z := foo(x, y);
        putint(z);
    end
