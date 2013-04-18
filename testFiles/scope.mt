! scopes
let var x: Integer;
    var y: Integer;
in
  begin
    x := 1;
    y := 2;
    let
      var x: Integer;
    in
      begin
        let
          var y: Integer;
        in
          getint(y);
        x := y;
      end
    putint(y);
    putint(x);
  end