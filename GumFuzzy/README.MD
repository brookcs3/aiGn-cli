Run 
1. go mod init fuzzy-picker
2. go mod tidy

This will automatically recreate the go.mod and go.sum files and fetch the dependencies for you.


If you want to use this as a real CLI tool, you can "install" it to your system path by running:

go install fuzzy_picker.go


(Remember we need to distribute this to class so , if we do that we need to remember to make setup scrip also do that )



To run go run fuzzy_picker.go