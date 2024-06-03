import pymysql.cursors

class db():

    marginpos=0.2

    def __init__(self):

        # Connect to the database
        self.conn = pymysql.connect(host='localhost',
                                    user='ghost',
                                    password='walks',
                                    database='ghostwalks',
                                    cursorclass=pymysql.cursors.DictCursor)
        self.cursor=self.conn.cursor()
    
    def insertPos(self,tagid,x,y):
        value=1
        sql = "INSERT INTO `positions` (`tagname`, `x`,`y`,`amount` ) VALUES (%s, %s,%s,%s)"
        self.cursor.execute(sql,(tagid,x,y,value))

        #now apply a reduced value in a ring of positions to make it more gradual
        rings=2

        for r in range(rings):
            d=(self.marginpos*r) #distance relative
            u=value/(r+2)
            #top left
            sql = "INSERT INTO `positions` (`tagname`, `x`,`y`,`amount` ) VALUES (%s, %s,%s,%s)"
            self.cursor.execute(sql,(tagid,x-d,y+d,u))
            #top
            sql = "INSERT INTO `positions` (`tagname`, `x`,`y`,`amount` ) VALUES (%s, %s,%s,%s)"
            self.cursor.execute(sql,(tagid,x,y+d,u))
            #top right
            sql = "INSERT INTO `positions` (`tagname`, `x`,`y`,`amount` ) VALUES (%s, %s,%s,%s)"
            self.cursor.execute(sql,(tagid,x+d,y+d,u))
            #right
            sql = "INSERT INTO `positions` (`tagname`, `x`,`y`,`amount` ) VALUES (%s, %s,%s,%s)"
            self.cursor.execute(sql,(tagid,x+d,y,u))
            #right bottom
            sql = "INSERT INTO `positions` (`tagname`, `x`,`y`,`amount` ) VALUES (%s, %s,%s,%s)"
            self.cursor.execute(sql,(tagid,x+d,y-d,u))
            #bottom
            sql = "INSERT INTO `positions` (`tagname`, `x`,`y`,`amount` ) VALUES (%s, %s,%s,%s)"
            self.cursor.execute(sql,(tagid,x,y-d,u))
            #bottom left
            sql = "INSERT INTO `positions` (`tagname`, `x`,`y`,`amount` ) VALUES (%s, %s,%s,%s)"
            self.cursor.execute(sql,(tagid,x-d,y-d,u))
            #left
            sql = "INSERT INTO `positions` (`tagname`, `x`,`y`,`amount` ) VALUES (%s, %s,%s,%s)"
            self.cursor.execute(sql,(tagid,x-d,y-d,u))

        self.conn.commit()

    def getHeatMapData(self):
        sql="SELECT "

    def getNormValue(self,x,y):
        #get total count
        sql = "SELECT SUM(*) as count FROM positions;"
        self.cursor.execute(sql)
        result = self.cursor.fetchone()
        total=result["count"]
        #get specific area count
        sql = "SELECT SUM(x) as count FROM positions WHERE x>"+str(x-self.marginpos)+" AND x<"+str(x+self.marginpos)+" AND y>"+str(y-self.marginpos)+" AND y<"+str(y+self.marginpos)+";"
        self.cursor.execute(sql)
        result = self.cursor.fetchone()
        local=result["count"]
        print("total",total,"local",local)
        if total==0 or local==0:
            return 0.0

        
        norm=(local/total)
        
       
        return norm