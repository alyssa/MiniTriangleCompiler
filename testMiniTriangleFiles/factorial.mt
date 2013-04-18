! Factorial
let 
    var x: Integer;
    var fact: Integer;
in
    begin
        getint(x);
        fact := 1;
        while x > 0 do
            begin
                fact := fact * x;
                x := x - 1;
            end
        putint(fact);
    end
