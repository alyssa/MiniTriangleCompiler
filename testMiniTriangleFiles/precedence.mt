! Precedence
let 
    var sum: Integer;
    var x: Integer;
    var y: Integer;
    var z: Integer;
in
    begin
        sum := 0;
        x := 1;
        y := 2;
        z := 3;
        sum := x + y*z; ! right: 7, wrong: 9
        putint(sum);
    end
