! scopes
let 
    var x: Integer;
    var y: Integer;
in
  begin
    x := 1;
    y := 2;
    let
      var x: Integer;
    in
      x := y;
    putint(x);
  end